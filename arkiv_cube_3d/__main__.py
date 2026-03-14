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
    if argv is None:
        return list(sys.argv[1:])

    args = list(argv)
    if args and Path(args[0]).name in {"__main__.py", "arkiv_cube_3d", "arkiv-cube-3d", "start_web.py"}:
        return args[1:]
    return args


def _build_parser(argv0: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_program_name(argv0),
        description="Start the local web control panel or run a Blender render.",
    )
    subcommands = parser.add_subparsers(dest="command")

    web_parser = subcommands.add_parser("web", help="Start the local web control panel.")
    web_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface for the web server (web command only).",
    )
    web_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for the web server (web command only).",
    )

    render_parser = subcommands.add_parser("render", help="Run a Blender render using bpy.")
    render_parser.add_argument(
        "--full",
        action="store_true",
        help="Run a full render instead of a fast preview (render command only).",
    )
    render_parser.add_argument(
        "--image",
        help="Load a fixed 23x23 PNG and use its colors with brightness-derived box heights (render command only).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw_args = _normalize_argv(argv)
    if not raw_args:
        raw_args = ["web"]
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

    if args.full:
        print("Starting full render...")
        out = render_cube.render_full(image_path=args.image)
    else:
        print("Starting fast preview render...")
        out = render_cube.render_fast(image_path=args.image)
    print(f"Render completed: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
