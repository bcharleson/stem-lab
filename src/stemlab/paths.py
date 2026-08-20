"""Session library paths. Never hardcode a machine home directory."""

from __future__ import annotations

import os
import re
from pathlib import Path

AUDIO_EXTENSIONS = {
    ".m4a",
    ".mp3",
    ".wav",
    ".flac",
    ".aiff",
    ".aif",
    ".ogg",
    ".aac",
    ".caf",
}

STEM_SETS = {
    2: ("drums", "no_drums"),
    4: ("vocals", "drums", "bass", "other"),
    6: ("vocals", "drums", "bass", "guitar", "piano", "other"),
}

DEFAULT_MODEL = {
    2: "htdemucs",
    4: "htdemucs",
    6: "htdemucs_6s",
}


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.strip().lower())
    return slug.strip("-") or "untitled"


def safe_filename(name: str) -> str:
    name = Path(name).name
    name = name.replace(":", "-").replace("/", "-").replace("\\", "-")
    return name or "audio"


def repo_root() -> Path:
    env = os.environ.get("STEM_LAB_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve()
    candidate = here.parents[2]
    if (candidate / "pyproject.toml").exists():
        return candidate
    return Path.cwd()


def work_dir() -> Path:
    env = os.environ.get("STEM_LAB_WORK")
    if env:
        return Path(env).expanduser().resolve()
    root = repo_root()
    if (root / "pyproject.toml").exists():
        return root / "work"
    return Path.cwd() / "work"


def session_dir(artist: str, title: str) -> Path:
    return work_dir() / slugify(artist) / slugify(title)


def find_source_audio(folder: Path) -> Path | None:
    source = folder / "source"
    search = source if source.is_dir() else folder
    if not search.is_dir():
        return None
    files = sorted(
        p for p in search.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    )
    return files[0] if files else None


def is_session_dir(folder: Path) -> bool:
    return (folder / "source").is_dir() and find_source_audio(folder) is not None
