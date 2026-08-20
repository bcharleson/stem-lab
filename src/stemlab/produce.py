"""Production mixdown: balance stems, sampled acoustic guitar, EQ/comp/reverb."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

from stemlab.guitar import VOICINGS, beat_times_from_audio, detect_chords, write_wav
from stemlab.paths import repo_root

STEM_TARGETS_LUFS = {
    "vocals": -18.0,
    "drums": -21.0,
    "bass": -21.0,
}

GUITAR_TARGET_LUFS = -19.0
MASTER_I = -13.0
SOUNDFONT_NAME = "MuseScore_General.sf3"
STEEL_GUITAR_PROGRAM = 25  # GM Acoustic Guitar (steel)


class ProduceError(RuntimeError):
    pass


def cache_dir() -> Path:
    path = repo_root() / ".cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def soundfont_path() -> Path:
    return cache_dir() / SOUNDFONT_NAME


def measure_lufs(path: Path) -> float:
    proc = subprocess.run(
        ["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    text = proc.stderr or ""
    idx = text.rfind("Integrated loudness:")
    chunk = text[idx : idx + 120] if idx >= 0 else text
    match = re.search(r"I:\s*([-\d.]+)\s*LUFS", chunk)
    if not match:
        raise ProduceError(f"Could not measure LUFS for {path}")
    return float(match.group(1))


def apply_gain_db(src: Path, dest: Path, gain_db: float) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-af",
        f"volume={gain_db:.2f}dB",
        "-c:a",
        "pcm_f32le",
        str(dest),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise ProduceError(proc.stderr[-400:] if proc.stderr else "ffmpeg volume failed")
    return dest


def balance_stem(src: Path, dest: Path, target_lufs: float) -> dict:
    current = measure_lufs(src)
    gain = target_lufs - current
    apply_gain_db(src, dest, gain)
    after = measure_lufs(dest)
    return {
        "file": str(dest),
        "before_lufs": round(current, 2),
        "target_lufs": target_lufs,
        "gain_db": round(gain, 2),
        "after_lufs": round(after, 2),
    }


def _chord_at(chords: list[tuple[float, float, str]], t: float) -> str:
    for t0, t1, name in chords:
        if t0 <= t < t1:
            return name
    return chords[-1][2] if chords else "G"


def write_country_midi(
    dest: Path,
    chords: list[tuple[float, float, str]],
    beat_times: np.ndarray,
    tempo: float,
) -> Path:
    import pretty_midi

    pm = pretty_midi.PrettyMIDI(initial_tempo=float(tempo))
    guitar = pretty_midi.Instrument(program=STEEL_GUITAR_PROGRAM, name="steel-acoustic")
    rng = np.random.default_rng(9)
    beats = [float(t) for t in beat_times]

    for i, t in enumerate(beats):
        name = _chord_at(chords, t)
        voicing = VOICINGS[name]
        t_next = beats[i + 1] if i + 1 < len(beats) else t + 0.7
        dur = min(0.58, max(0.30, (t_next - t) * 0.88))
        beat_in_bar = i % 4
        t_h = max(0.0, t + float(rng.uniform(-0.012, 0.012)))

        if beat_in_bar in (0, 2):
            vel = int(rng.integers(84, 98)) if beat_in_bar == 0 else int(rng.integers(76, 90))
            guitar.notes.append(
                pretty_midi.Note(velocity=vel, pitch=voicing[0], start=t_h, end=t_h + dur)
            )
            if len(voicing) > 1:
                guitar.notes.append(
                    pretty_midi.Note(
                        velocity=max(55, vel - 10),
                        pitch=voicing[1],
                        start=t_h + 0.012,
                        end=t_h + dur,
                    )
                )
        else:
            notes = voicing[-4:] if len(voicing) >= 4 else voicing
            vel = int(rng.integers(72, 94))
            for j, pitch in enumerate(notes):
                stagger = j * 0.010
                guitar.notes.append(
                    pretty_midi.Note(
                        velocity=max(52, vel - j * 3),
                        pitch=pitch,
                        start=t_h + stagger,
                        end=t_h + stagger + dur * 0.72,
                    )
                )

        if beat_in_bar == 0:
            for j, pitch in enumerate(voicing):
                guitar.notes.append(
                    pretty_midi.Note(
                        velocity=int(rng.integers(56, 68)),
                        pitch=pitch,
                        start=t_h + j * 0.008,
                        end=t_h + dur + 0.06,
                    )
                )

    pm.instruments.append(guitar)
    dest.parent.mkdir(parents=True, exist_ok=True)
    pm.write(str(dest))
    return dest


def render_midi(midi_path: Path, wav_path: Path, sr: int = 44100) -> Path:
    font = soundfont_path()
    if not font.is_file():
        raise ProduceError(
            f"Soundfont missing: {font}. Download MuseScore_General.sf3 into .cache/"
        )
    fluidsynth = shutil.which("fluidsynth")
    if fluidsynth is None:
        raise ProduceError("fluidsynth not found — brew install fluid-synth")
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        fluidsynth,
        "-ni",
        "-g",
        "0.7",
        f"--fast-render={wav_path}",
        "-r",
        str(sr),
        "-R",
        "1",
        "-C",
        "0",
        str(font),
        str(midi_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not wav_path.is_file():
        raise ProduceError(proc.stderr[-500:] if proc.stderr else "fluidsynth failed")
    return wav_path


def match_length(src: Path, n_samples: int, sr: int, dest: Path) -> Path:
    audio, file_sr = sf.read(src, always_2d=True)
    if file_sr != sr:
        import librosa

        audio = np.stack(
            [librosa.resample(audio[:, c], orig_sr=file_sr, target_sr=sr) for c in range(audio.shape[1])],
            axis=1,
        )
    if audio.shape[0] < n_samples:
        pad = np.zeros((n_samples - audio.shape[0], audio.shape[1]), dtype=audio.dtype)
        audio = np.concatenate([audio, pad], axis=0)
    else:
        audio = audio[:n_samples]
    return write_wav(dest, audio.astype(np.float32), sr)


def mixdown_country(vocals: Path, drums: Path, bass: Path, guitar: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    raw = dest.with_name(dest.stem + ".pre-limit.wav")
    filt = (
        "[0:a]highpass=f=80,acompressor=threshold=0.112:ratio=3:attack=12:release=90:makeup=3,"
        "equalizer=f=3200:t=q:w=1.1:g=2.2,aecho=0.8:0.88:92:0.16,volume=1.12[v];"
        "[1:a]highpass=f=45,acompressor=threshold=0.14:ratio=2.2:attack=6:release=70:makeup=1,"
        "volume=0.78[d];"
        "[2:a]highpass=f=38,lowpass=f=280,acompressor=threshold=0.16:ratio=3:attack=10:release=140:makeup=1,"
        "volume=0.62[b];"
        "[3:a]highpass=f=90,equalizer=f=2200:t=q:w=1.0:g=1.8,aecho=0.75:0.8:48:0.12,volume=1.08[g];"
        "[v][d][b][g]amix=inputs=4:duration=longest:normalize=0:dropout_transition=0,"
        "alimiter=limit=0.94"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(vocals),
        "-i",
        str(drums),
        "-i",
        str(bass),
        "-i",
        str(guitar),
        "-filter_complex",
        filt,
        "-c:a",
        "pcm_f32le",
        str(raw),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise ProduceError(proc.stderr[-600:] if proc.stderr else "ffmpeg mixdown failed")

    loud = [
        "ffmpeg",
        "-y",
        "-i",
        str(raw),
        "-af",
        f"loudnorm=I={MASTER_I}:TP=-1.5:LRA=9",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-c:a",
        "pcm_f32le",
        str(dest),
    ]
    proc = subprocess.run(loud, capture_output=True, text=True, check=False)
    raw.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise ProduceError(proc.stderr[-400:] if proc.stderr else "ffmpeg loudnorm failed")
    return dest


def produce_country(session: Path, model: str = "htdemucs") -> dict:
    stem_dir = session / "stems" / model
    vocals_src = stem_dir / "vocals.wav"
    drums_src = stem_dir / "drums.wav"
    bass_src = stem_dir / "bass.wav"
    other_src = stem_dir / "other.wav"
    for p in (vocals_src, drums_src, bass_src, other_src):
        if not p.is_file():
            raise ProduceError(f"Missing stem: {p}")

    drums, sr = sf.read(drums_src, always_2d=True)
    bass, _ = sf.read(bass_src, always_2d=True)
    other, _ = sf.read(other_src, always_2d=True)
    n_samples = drums.shape[0]
    harmonic = 0.65 * bass + 1.0 * other
    tempo, beats = beat_times_from_audio(drums, sr)
    chords = detect_chords(harmonic, sr, beats, beats_per_chord=2)

    gen_dir = session / "stems" / "generated"
    balanced = session / "stems" / "balanced"
    midi_path = write_country_midi(gen_dir / "acoustic_guitar.mid", chords, beats, tempo)
    raw_g = render_midi(midi_path, gen_dir / "acoustic_guitar.raw.wav", sr=sr)
    guitar_full = match_length(raw_g, n_samples, sr, gen_dir / "acoustic_guitar.unbalanced.wav")
    raw_g.unlink(missing_ok=True)

    reports = {
        "vocals": balance_stem(vocals_src, balanced / "vocals.wav", STEM_TARGETS_LUFS["vocals"]),
        "drums": balance_stem(drums_src, balanced / "drums.wav", STEM_TARGETS_LUFS["drums"]),
        "bass": balance_stem(bass_src, balanced / "bass.wav", STEM_TARGETS_LUFS["bass"]),
        "guitar": balance_stem(guitar_full, gen_dir / "acoustic_guitar.wav", GUITAR_TARGET_LUFS),
    }
    guitar_full.unlink(missing_ok=True)

    mix_path = mixdown_country(
        Path(reports["vocals"]["file"]),
        Path(reports["drums"]["file"]),
        Path(reports["bass"]["file"]),
        Path(reports["guitar"]["file"]),
        session / "remixes" / "country-acoustic.wav",
    )
    mix_lufs = measure_lufs(mix_path)
    compact = [{"start": round(a, 2), "end": round(b, 2), "chord": c} for a, b, c in chords]
    return {
        "success": True,
        "style": "country-acoustic",
        "vocal": "original",
        "tempo": round(float(tempo), 2),
        "mix": str(mix_path),
        "mix_lufs": round(mix_lufs, 2),
        "stems": reports,
        "chords": compact[:40],
        "chord_count": len(compact),
    }
