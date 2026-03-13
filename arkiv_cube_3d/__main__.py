"""Module entrypoint so the package can be run with `python -m arkiv_cube_3d`.

Default behavior: start the web server (safe in non-Blender environments).
Subcommands:
  render    - perform a direct render using Blender's bpy (requires bpy)
  web       - start the local web control panel (default)

Examples:
  python -m arkiv_cube_3d
  python -m arkiv_cube_3d web
  python -m arkiv_cube_3d render
"""
from __future__ import annotations

import sys
from typing import Sequence

from . import render_cube, web_server


def _usage(argv: Sequence[str]) -> str:
    name = argv[0] if argv else "python -m arkiv_cube_3d"
    return f"Usage: {name} [web|render]\n\n" \
           f"Commands:\n  web     Start the local web control panel (default)\n  render  Run a single render using Blender (requires bpy)\n"


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(argv or sys.argv)

    # pop module name when invoked via -m
    if len(argv) and argv[0].endswith("arkiv_cube_3d"):
        argv = argv[1:]

    if not argv:
        # no args -> default to web
        cmd = "web"
    else:
        cmd = argv[0]

    if cmd in ("-h", "--help"):
        print(_usage(sys.argv))
        return 0

    if cmd == "web":
        # start the web server
        try:
            web_server.main()
            return 0
        except Exception as exc:  # pragma: no cover - run-time behavior
            print(f"Failed to start web server: {exc}", file=sys.stderr)
            return 2

    if cmd == "render":
        # perform a render using default params
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

    print(f"Unknown command: {cmd}\n", file=sys.stderr)
    print(_usage(sys.argv), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

