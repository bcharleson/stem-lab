from stemlab.paths import slugify, safe_filename, STEM_SETS
from stemlab.mix import select_stems
from pathlib import Path


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
