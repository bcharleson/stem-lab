"""Time-locked acoustic guitar accompaniment from a session's harmonic stems."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Open-position guitar voicings (MIDI). Country I–IV–V–vi in G.
VOICINGS: dict[str, list[int]] = {
    "G": [43, 47, 50, 55, 59, 67],
    "C": [48, 52, 55, 60, 64, 67],
    "D": [50, 57, 62, 66],
    "D7": [50, 54, 57, 60, 66],
    "Em": [40, 47, 52, 55, 59, 64],
    "Am": [45, 52, 57, 60, 64],
}

KEY_CHORDS = {
    "G": ("G", "C", "D", "D7", "Em", "Am"),
}


def midi_to_hz(midi: float) -> float:
    return 440.0 * (2.0 ** ((midi - 69.0) / 12.0))


def _karplus_strong(freq: float, n: int, sr: int, decay: float) -> np.ndarray:
    period = max(2, int(round(sr / freq)))
    buf = np.random.randn(period).astype(np.float32)
    buf -= buf.mean()
    out = np.zeros(n, dtype=np.float32)
    out[:period] = buf
    for i in range(period, n):
        prev = out[i - period]
        prev2 = out[i - period - 1] if i > period else prev
        out[i] = decay * 0.5 * (prev + prev2)
    # cheap pick attack + decay envelope
    env = np.linspace(1.0, 0.15, n, dtype=np.float32)
    return out * env


def _pluck_bank(sr: int, duration: float = 2.2) -> dict[int, np.ndarray]:
    n = int(sr * duration)
    bank: dict[int, np.ndarray] = {}
    midis = sorted({m for v in VOICINGS.values() for m in v})
    for midi in midis:
        # slightly less decay on higher strings
        decay = 0.988 if midi < 55 else 0.992
        bank[midi] = _karplus_strong(midi_to_hz(midi), n, sr, decay)
    return bank


def _add(dest: np.ndarray, src: np.ndarray, at: int, gain: float) -> None:
    if at >= dest.shape[0]:
        return
    sl = src[: dest.shape[0] - at] * gain
    dest[at : at + sl.shape[0]] += sl


def _template(name: str) -> np.ndarray:
    pcs = [m % 12 for m in VOICINGS[name]]
    vec = np.zeros(12, dtype=np.float32)
    for i, pc in enumerate(pcs):
        vec[pc] += 1.0 if i == 0 else 0.75
    return vec / (np.linalg.norm(vec) + 1e-9)


def detect_chords(
    harmonic: np.ndarray,
    sr: int,
    beat_times: np.ndarray,
    palette: tuple[str, ...] = KEY_CHORDS["G"],
    beats_per_chord: int = 2,
) -> list[tuple[float, float, str]]:
    import librosa

    templates = {name: _template(name) for name in palette}
    y = harmonic.mean(axis=1).astype(np.float32) if harmonic.ndim == 2 else harmonic.astype(np.float32)
    hop = 512
    target = 22050
    if sr != target:
        y = librosa.resample(y, orig_sr=sr, target_sr=target)
        use_sr = target
    else:
        use_sr = sr
    chroma = librosa.feature.chroma_cqt(y=y, sr=use_sr, hop_length=hop)
    frame_t = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=use_sr, hop_length=hop)
    times = np.concatenate([beat_times, [harmonic.shape[0] / sr]])
    chords: list[tuple[float, float, str]] = []
    for i in range(0, len(times) - 1, beats_per_chord):
        t0 = float(times[i])
        t1 = float(times[min(i + beats_per_chord, len(times) - 1)])
        mask = (frame_t >= t0) & (frame_t < t1)
        vec = chroma[:, mask].mean(axis=1) if np.any(mask) else chroma.mean(axis=1)
        vec = vec / (np.linalg.norm(vec) + 1e-9)
        name = max(templates, key=lambda n: float(vec @ templates[n]))
        if chords and chords[-1][2] == name:
            chords[-1] = (chords[-1][0], t1, name)
        else:
            chords.append((t0, t1, name))
    return chords


def beat_times_from_audio(y: np.ndarray, sr: int) -> tuple[float, np.ndarray]:
    import librosa

    mono = y.mean(axis=1).astype(np.float32) if y.ndim == 2 else y.astype(np.float32)
    target = 22050
    a = librosa.resample(mono, orig_sr=sr, target_sr=target)
    tempo, beats = librosa.beat.beat_track(y=a, sr=target, units="time")
    tempo = float(np.atleast_1d(tempo)[0])
    # Country pocket is ~80–95; fold double-time detections.
    if tempo > 120:
        tempo = tempo / 2.0
        beats = beats[::2]
    return tempo, beats.astype(float)


def render_country_acoustic(
    n_samples: int,
    sr: int,
    chords: list[tuple[float, float, str]],
    beat_times: np.ndarray,
) -> np.ndarray:
    rng = np.random.default_rng(7)
    bank = _pluck_bank(sr)
    left = np.zeros(n_samples, dtype=np.float32)
    right = np.zeros(n_samples, dtype=np.float32)
    beat_times = np.concatenate([beat_times, [n_samples / sr]])

    def chord_at(t: float) -> str:
        for t0, t1, name in chords:
            if t0 <= t < t1:
                return name
        return chords[-1][2] if chords else "G"

    for i, t in enumerate(beat_times[:-1]):
        name = chord_at(float(t))
        voicing = VOICINGS[name]
        at = int(float(t) * sr)
        beat_in_bar = i % 4
        width = int(0.008 * sr)

        if beat_in_bar in (0, 2):
            # boom: low strings
            notes = voicing[:2]
            gain = 0.22 if beat_in_bar == 0 else 0.18
            for midi in notes:
                pluck = bank[midi]
                _add(left, pluck, at, gain)
                _add(right, pluck, at + width, gain * 0.85)
        else:
            # chuck: upper strings, slightly muted
            notes = voicing[-4:] if len(voicing) >= 4 else voicing
            gain = 0.16
            for j, midi in enumerate(notes):
                pluck = bank[midi] * 0.7
                jitter = int(rng.integers(0, 120))
                g = gain * (0.9 + 0.2 * (j / max(1, len(notes) - 1)))
                _add(left, pluck, at + jitter, g)
                _add(right, pluck, at + jitter + width, g)

        # fuller downstrum on the downbeat of a chord change
        if beat_in_bar == 0:
            for j, midi in enumerate(voicing):
                pluck = bank[midi]
                stagger = int(j * 0.004 * sr)
                g = 0.09
                _add(left, pluck, at + stagger, g)
                _add(right, pluck, at + stagger + width, g)

    stereo = np.stack([left, right], axis=1)
    peak = np.max(np.abs(stereo)) + 1e-9
    stereo = stereo * (0.6 / peak)
    return stereo


def build_country_guitar(harmonic: np.ndarray, sr: int, beat_source: np.ndarray) -> tuple[np.ndarray, list[tuple[float, float, str]], float]:
    tempo, beats = beat_times_from_audio(beat_source, sr)
    chords = detect_chords(harmonic, sr, beats, beats_per_chord=2)
    guitar = render_country_acoustic(harmonic.shape[0], sr, chords, beats)
    return guitar, chords, tempo


def mix_country_keep_vocal(
    vocals: np.ndarray,
    drums: np.ndarray,
    bass: np.ndarray,
    guitar: np.ndarray,
    sr: int,
) -> np.ndarray:
    """Keep the original vocal; sit a country band under it."""
    n = min(vocals.shape[0], drums.shape[0], bass.shape[0], guitar.shape[0])
    v = vocals[:n].astype(np.float32)
    d = drums[:n].astype(np.float32)
    b = bass[:n].astype(np.float32)
    g = guitar[:n].astype(np.float32)

    # ~95 ms country slapback on the vocal, one repeat
    delay = int(0.095 * sr)
    slap = np.zeros_like(v)
    slap[delay:] = v[:-delay] * 0.22
    v = v + slap

    mix = v * 1.18 + d * 0.58 + b * 0.28 + g * 1.40
    peak = np.max(np.abs(mix)) + 1e-9
    mix = mix * (0.89 / peak)
    return mix


def write_wav(path: Path, audio: np.ndarray, sr: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, audio, sr, subtype="FLOAT")
    return path
