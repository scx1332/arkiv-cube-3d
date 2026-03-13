"""Module entrypoint so the package can be run with `python -m arkiv_cube_3d`."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

from . import render_cube, web_server


def _program_name(argv0: str | None = None) -> str:
    name = Path(argv0 or sys.argv[0]).name
    if name == "__main__.py":
        return "python -m arkiv_cube_3d"
    return name or "python -m arkiv_cube_3d"


def _normalize_argv(argv: Sequence[str] | None) -> list[str]:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and Path(args[0]).name in {"__main__.py", "arkiv_cube_3d", "arkiv-cube-3d", "start_web.py"}:
        return args[1:]
    if args and Path(args[0]).suffix == ".py":
        return args[1:]
    return args


def _build_parser(argv0: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_program_name(argv0),
        description="Start the local web control panel or run a Blender render.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("web", "render"),
        default="web",
        help="Command to run (defaults to %(default)s).",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface for the web server (web command only).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for the web server (web command only).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw_args = _normalize_argv(argv)
    parser = _build_parser()

    try:
        args = parser.parse_args(raw_args)
    except SystemExit as exc:
        return int(exc.code or 0)

    if args.command == "web":
        try:
            web_server.main(host=args.host, port=args.port)
            return 0
        except Exception as exc:  # pragma: no cover - run-time behavior
            print(f"Failed to start web server: {exc}", file=sys.stderr)
            return 2

    if not render_cube.is_bpy_available():
        print(
            "bpy is not available in this Python environment.\n"
            "To run rendering, either run through Blender or install the `bpy` package.",
            file=sys.stderr,
        )
        return 3

    try:
        out = render_cube.main()
        print(f"Render completed: {out}")
        return 0
    except Exception as exc:  # pragma: no cover - run-time behavior
        print(f"Render failed: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
