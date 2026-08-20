"""stem-lab command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from stemlab import __version__
from stemlab.doctor import format_checks, run_checks, all_ok
from stemlab.extract import ExtractError, extract
from stemlab.mix import MixError, list_available_stems, mix_stems, select_stems
from stemlab.paths import (
    DEFAULT_MODEL,
    STEM_SETS,
    is_session_dir,
    safe_filename,
    session_dir,
    work_dir,
)
from stemlab.session import create_session, record_extract, require_source


def _print(result: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, indent=2))
        return
    if not result.get("success", True) and "error" in result:
        print(result["error"], file=sys.stderr)
        return
    for key, value in result.items():
        if key == "outputs" and isinstance(value, dict):
            print("outputs:")
            for name, path in value.items():
                print(f"  {name}: {path}")
        else:
            print(f"{key}: {value}")


def cmd_doctor(args: argparse.Namespace) -> int:
    checks = run_checks()
    if args.json:
        print(json.dumps({"success": all_ok(checks), "checks": checks}, indent=2))
    else:
        print(format_checks(checks))
    return 0 if all_ok(checks) else 1


def cmd_ingest(args: argparse.Namespace) -> int:
    source = args.file.expanduser().resolve()
    if not source.is_file():
        _print({"success": False, "error": f"File not found: {source}"}, args.json)
        return 1
    dest_name = safe_filename(source.name)
    folder = create_session(args.artist, args.title, source, dest_name=dest_name)
    result = {
        "success": True,
        "session": str(folder),
        "artist": args.artist,
        "title": args.title,
        "source": str(folder / "source" / dest_name),
    }
    _print(result, args.json)
    return 0


def _resolve_session(args: argparse.Namespace) -> Path | None:
    if args.artist and args.title:
        return session_dir(args.artist, args.title)
    if args.path and args.path.is_dir() and is_session_dir(args.path):
        return args.path.expanduser().resolve()
    if args.path and args.path.is_file():
        parent = args.path.expanduser().resolve().parent
        if parent.name == "source" and is_session_dir(parent.parent):
            return parent.parent
    return None


def cmd_extract(args: argparse.Namespace) -> int:
    session = _resolve_session(args)
    try:
        if session is not None:
            audio = require_source(session)
            dest = session / "stems" / (args.model or DEFAULT_MODEL[args.stems])
        elif args.path and args.path.is_file():
            audio = args.path.expanduser().resolve()
            dest = Path.cwd() / "output" / (args.model or DEFAULT_MODEL[args.stems]) / audio.stem
        else:
            _print(
                {
                    "success": False,
                    "error": "Pass an audio file, a session directory, or --artist and --title",
                },
                args.json,
            )
            return 1

        result = extract(
            audio,
            dest,
            stems=args.stems,
            model=args.model,
            mp3=args.mp3,
            float32=not args.mp3,
            quiet=args.quiet or args.json,
        )
        if session is not None:
            rel = {
                name: str(Path(path).relative_to(session))
                for name, path in result["outputs"].items()
            }
            record_extract(
                session,
                model=result["model"],
                stems=result["stems"],
                files=rel,
            )
            result["session"] = str(session)
    except (ExtractError, FileNotFoundError) as exc:
        _print({"success": False, "error": str(exc)}, args.json)
        return 1

    _print(result, args.json)
    return 0


def cmd_mix(args: argparse.Namespace) -> int:
    session = _resolve_session(args)
    if session is None:
        if args.path and args.path.is_dir():
            stem_folder = args.path.expanduser().resolve()
            session = stem_folder
        else:
            _print({"success": False, "error": "Pass a stems directory or --artist and --title"}, args.json)
            return 1
    else:
        model = args.model or DEFAULT_MODEL[4]
        stem_folder = session / "stems" / model
        if not stem_folder.is_dir():
            stems_root = session / "stems"
            sub = sorted(p for p in stems_root.glob("*") if p.is_dir()) if stems_root.is_dir() else []
            if not sub:
                _print({"success": False, "error": f"No stems in {stems_root}"}, args.json)
                return 1
            stem_folder = sub[-1]

    available = list_available_stems(stem_folder)
    if not available:
        _print({"success": False, "error": f"No stem files in {stem_folder}"}, args.json)
        return 1

    try:
        inputs = select_stems(available, mute=args.mute, solo=args.solo)
        default_out = session / "remixes" / "mix.wav" if (session / "remixes").exists() else Path.cwd() / "mix.wav"
        output = args.out.expanduser().resolve() if args.out else default_out
        mixed = mix_stems(inputs, output)
    except MixError as exc:
        _print({"success": False, "error": str(exc)}, args.json)
        return 1

    _print(
        {
            "success": True,
            "output": str(mixed),
            "stems": [p.stem for p in inputs],
        },
        args.json,
    )
    return 0


def cmd_lib(_args: argparse.Namespace) -> int:
    path = work_dir()
    path.mkdir(parents=True, exist_ok=True)
    print(path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stem-lab",
        description="Extract full-band stems and rebuild mixes locally with Demucs.",
    )
    parser.add_argument("--version", action="version", version=f"stem-lab {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    doctor = sub.add_parser("doctor", help="Check ffmpeg, demucs, and work dir")
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(func=cmd_doctor)

    ingest = sub.add_parser("ingest", help="Copy a track into work/<artist>/<title>/")
    ingest.add_argument("file", type=Path)
    ingest.add_argument("--artist", required=True)
    ingest.add_argument("--title", required=True)
    ingest.add_argument("--json", action="store_true")
    ingest.set_defaults(func=cmd_ingest)

    extract_p = sub.add_parser("extract", help="Separate stems (default: 4)")
    extract_p.add_argument("path", nargs="?", type=Path, help="Audio file or session directory")
    extract_p.add_argument("--artist")
    extract_p.add_argument("--title")
    extract_p.add_argument("--stems", type=int, choices=sorted(STEM_SETS), default=4)
    extract_p.add_argument("-n", "--model", help="Demucs model (default from --stems)")
    extract_p.add_argument("--mp3", action="store_true")
    extract_p.add_argument("--json", action="store_true")
    extract_p.add_argument("--quiet", action="store_true")
    extract_p.set_defaults(func=cmd_extract)

    mix = sub.add_parser("mix", help="Rebuild a mix from extracted stems")
    mix.add_argument("path", nargs="?", type=Path, help="Session or stems directory")
    mix.add_argument("--artist")
    mix.add_argument("--title")
    mix.add_argument("-n", "--model")
    mix.add_argument("--mute", nargs="*", default=[], help="Stem names to drop")
    mix.add_argument("--solo", nargs="*", default=[], help="Only these stems")
    mix.add_argument("-o", "--out", type=Path)
    mix.add_argument("--json", action="store_true")
    mix.set_defaults(func=cmd_mix)

    lib = sub.add_parser("lib", help="Print the local work directory")
    lib.set_defaults(func=cmd_lib)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
