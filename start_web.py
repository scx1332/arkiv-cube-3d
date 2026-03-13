"""Convenience launcher for the local web control panel."""

from __future__ import annotations

import sys

from arkiv_cube_3d.__main__ import main


if __name__ == "__main__":
    raise SystemExit(main(["web", *sys.argv[1:]]))
