"""Environment checks. Prints local paths at runtime; none are compiled into the repo."""

from __future__ import annotations

import shutil
import sys

from stemlab.paths import work_dir


def _ok(label: str, detail: str) -> dict:
    return {"ok": True, "label": label, "detail": detail}


def _fail(label: str, detail: str) -> dict:
    return {"ok": False, "label": label, "detail": detail}


def run_checks() -> list[dict]:
    checks: list[dict] = []
    py = sys.version.split()[0]
    if sys.version_info >= (3, 10):
        checks.append(_ok("python", py))
    else:
        checks.append(_fail("python", f"{py} (need 3.10+)"))

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        checks.append(_ok("ffmpeg", ffmpeg))
    else:
        checks.append(_fail("ffmpeg", "not found — install ffmpeg"))

    demucs = shutil.which("demucs")
    if demucs:
        checks.append(_ok("demucs", demucs))
    else:
        checks.append(_fail("demucs", "not found — run ./scripts/install.sh"))

    work = work_dir()
    try:
        work.mkdir(parents=True, exist_ok=True)
        probe = work / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        checks.append(_ok("work", str(work)))
    except OSError as exc:
        checks.append(_fail("work", f"{work} not writable ({exc})"))

    return checks


def all_ok(checks: list[dict]) -> bool:
    return all(c["ok"] for c in checks)


def format_checks(checks: list[dict]) -> str:
    lines = ["stem-lab doctor"]
    for c in checks:
        mark = "ok" if c["ok"] else "FAIL"
        lines.append(f"  [{mark}] {c['label']}: {c['detail']}")
    lines.append("Ready." if all_ok(checks) else "Fix the items above.")
    return "\n".join(lines)
