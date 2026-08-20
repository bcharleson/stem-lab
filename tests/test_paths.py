from pathlib import Path

import numpy as np

from stemlab.guitar import KEY_CHORDS, VOICINGS, midi_to_hz, render_reggae_skank
from stemlab.mix import select_stems
from stemlab.paths import STEM_SETS, safe_filename, slugify


def test_slugify_artist_and_title():
    assert slugify("Example Artist") == "example-artist"
    assert slugify("Demo Song") == "demo-song"
    assert slugify("  Hello, World!  ") == "hello-world"


def test_safe_filename_strips_colon():
    assert ":" not in safe_filename("Track - Mix - 4:24:24.m4a")
    assert safe_filename("/tmp/track/name.wav") == "name.wav"


def test_stem_sets():
    assert STEM_SETS[2] == ("drums", "no_drums")
    assert "vocals" in STEM_SETS[4]
    assert "guitar" in STEM_SETS[6]


def test_select_stems_mute_and_solo(tmp_path: Path):
    available = {
        "vocals": tmp_path / "vocals.wav",
        "drums": tmp_path / "drums.wav",
        "bass": tmp_path / "bass.wav",
        "other": tmp_path / "other.wav",
    }
    muted = select_stems(available, mute=["vocals"])
    assert [p.stem for p in muted] == ["drums", "bass", "other"]
    solo = select_stems(available, solo=["vocals", "drums"])
    assert [p.stem for p in solo] == ["vocals", "drums"]


def test_guitar_voicings_and_tuning():
    assert abs(midi_to_hz(69) - 440.0) < 1e-6
    assert abs(midi_to_hz(57) - 220.0) < 1e-6
    for name in KEY_CHORDS["G"]:
        assert name in VOICINGS
        assert len(VOICINGS[name]) >= 4


def test_reggae_skank_is_stereo_and_bounded():
    sr = 8000
    n = sr * 2
    chords = [(0.0, 2.0, "G")]
    beats = np.array([0.0, 0.5, 1.0, 1.5], dtype=float)
    out = render_reggae_skank(n, sr, chords, beats)
    assert out.shape == (n, 2)
    assert np.max(np.abs(out)) <= 0.66
