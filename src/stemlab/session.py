"""Session metadata — relative paths only, no machine-specific locations."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from stemlab.paths import find_source_audio, session_dir


def session_json_path(folder: Path) -> Path:
    return folder / "session.json"


def load_session(folder: Path) -> dict[str, Any]:
    path = session_json_path(folder)
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_session(folder: Path, data: dict[str, Any]) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = session_json_path(folder)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def ensure_layout(folder: Path) -> None:
    for name in ("source", "stems", "remixes"):
        (folder / name).mkdir(parents=True, exist_ok=True)


def create_session(artist: str, title: str, source: Path, dest_name: str | None = None) -> Path:
    folder = session_dir(artist, title)
    ensure_layout(folder)
    dest_name = dest_name or source.name
    dest = folder / "source" / dest_name
    if source.resolve() != dest.resolve():
        dest.write_bytes(source.read_bytes())
    data = load_session(folder)
    data.update(
        {
            "artist": artist,
            "title": title,
            "source_file": f"source/{dest_name}",
            "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )
    data.setdefault("extracts", [])
    save_session(folder, data)
    return folder


def record_extract(
    folder: Path,
    *,
    model: str,
    stems: int,
    files: dict[str, str],
) -> None:
    data = load_session(folder)
    extracts = data.setdefault("extracts", [])
    entry = {
        "model": model,
        "stems": stems,
        "dir": f"stems/{model}",
        "files": files,
        "extracted": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    extracts = [e for e in extracts if not (e.get("model") == model and e.get("stems") == stems)]
    extracts.append(entry)
    data["extracts"] = extracts
    save_session(folder, data)


def require_source(folder: Path) -> Path:
    audio = find_source_audio(folder)
    if audio is None:
        raise FileNotFoundError(f"No source audio in {folder / 'source'}")
    return audio
