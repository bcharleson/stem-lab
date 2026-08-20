"""Rebuild a mix from selected stems with ffmpeg."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from stemlab.paths import STEM_SETS


class MixError(RuntimeError):
    pass


def ffmpeg_bin() -> str:
    binary = shutil.which("ffmpeg")
    if binary is None:
        raise MixError("ffmpeg not found on PATH")
    return binary


def list_available_stems(folder: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for ext in ("wav", "mp3", "flac"):
        for path in folder.glob(f"*.{ext}"):
            found[path.stem] = path
    return found


def select_stems(
    available: dict[str, Path],
    *,
    mute: list[str] | None = None,
    solo: list[str] | None = None,
) -> list[Path]:
    mute_set = {s.lower() for s in (mute or [])}
    solo_set = {s.lower() for s in (solo or [])}
    names = list(available)
    if solo_set:
        names = [n for n in names if n.lower() in solo_set]
    names = [n for n in names if n.lower() not in mute_set]
    if not names:
        raise MixError("No stems left after mute/solo filters")
    # Keep canonical band order when possible
    order = list(STEM_SETS[6]) + ["no_drums"]
    names.sort(key=lambda n: order.index(n) if n in order else 99)
    return [available[n] for n in names]


def mix_stems(inputs: list[Path], output: Path) -> Path:
    if not inputs:
        raise MixError("No stem files to mix")
    output.parent.mkdir(parents=True, exist_ok=True)
    if len(inputs) == 1:
        shutil.copy2(inputs[0], output)
        return output

    cmd = [ffmpeg_bin(), "-y"]
    for path in inputs:
        cmd.extend(["-i", str(path)])
    n = len(inputs)
    cmd.extend(
        [
            "-filter_complex",
            f"amix=inputs={n}:duration=longest:dropout_transition=0:normalize=0",
            str(output),
        ]
    )
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise MixError(proc.stderr.strip() or "ffmpeg mix failed")
    return output
