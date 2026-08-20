"""Run Demucs and stage stems into a session or ./output."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from stemlab.paths import DEFAULT_MODEL, STEM_SETS


class ExtractError(RuntimeError):
    pass


def demucs_bin() -> str:
    binary = shutil.which("demucs")
    if binary is None:
        raise ExtractError(
            "demucs not found on PATH. From the repo: ./scripts/install.sh"
        )
    return binary


def run_demucs(
    input_path: Path,
    output_dir: Path,
    *,
    model: str,
    stems: int,
    mp3: bool,
    float32: bool,
    quiet: bool,
) -> subprocess.CompletedProcess[str]:
    cmd = [demucs_bin(), "-n", model, "-o", str(output_dir)]
    if stems == 2:
        cmd.extend(["--two-stems", "drums"])
    if mp3:
        cmd.append("--mp3")
    if float32 and not mp3:
        cmd.append("--float32")
    cmd.append(str(input_path))
    return subprocess.run(
        cmd,
        capture_output=quiet,
        text=True,
        check=False,
    )


def find_demucs_folder(output_dir: Path, model: str, stem_names: tuple[str, ...], ext: str) -> Path:
    model_dir = output_dir / model
    if not model_dir.is_dir():
        raise ExtractError(f"Demucs output missing: {model_dir}")
    for sub in sorted(model_dir.iterdir()):
        if not sub.is_dir():
            continue
        if all((sub / f"{name}.{ext}").is_file() for name in stem_names):
            return sub
    raise ExtractError(f"Could not find {list(stem_names)} under {model_dir}")


def copy_stems(src_folder: Path, dest_folder: Path, stem_names: tuple[str, ...], ext: str) -> dict[str, Path]:
    dest_folder.mkdir(parents=True, exist_ok=True)
    copied: dict[str, Path] = {}
    for name in stem_names:
        src = src_folder / f"{name}.{ext}"
        dest = dest_folder / f"{name}.{ext}"
        shutil.copy2(src, dest)
        copied[name] = dest
    return copied


def extract(
    input_path: Path,
    dest_folder: Path,
    *,
    stems: int = 4,
    model: str | None = None,
    mp3: bool = False,
    float32: bool = True,
    quiet: bool = False,
) -> dict:
    if stems not in STEM_SETS:
        raise ExtractError(f"stems must be one of {sorted(STEM_SETS)}")
    input_path = input_path.expanduser().resolve()
    if not input_path.is_file():
        raise ExtractError(f"Input file not found: {input_path}")

    model = model or DEFAULT_MODEL[stems]
    stem_names = STEM_SETS[stems]
    ext = "mp3" if mp3 else "wav"
    dest_folder = dest_folder.expanduser().resolve()
    dest_folder.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    tmp = Path(tempfile.mkdtemp(prefix="stem-lab-"))
    try:
        proc = run_demucs(
            input_path,
            tmp,
            model=model,
            stems=stems,
            mp3=mp3,
            float32=float32,
            quiet=quiet,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "demucs failed").strip()
            raise ExtractError(err)
        src_folder = find_demucs_folder(tmp, model, stem_names, ext)
        copied = copy_stems(src_folder, dest_folder, stem_names, ext)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    elapsed = round(time.perf_counter() - started, 2)
    return {
        "success": True,
        "input": str(input_path),
        "model": model,
        "stems": stems,
        "duration_seconds": elapsed,
        "outputs": {name: str(path) for name, path in copied.items()},
    }
