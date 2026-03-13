"""Pure geometry helpers for Blender mesh construction."""

import json
from pathlib import Path


BOX_DEFAULT_SIZE = 1.9
BOX_CONFIGS = [
    ("Box_",(0, 0-10, 1.0), BOX_DEFAULT_SIZE),
    ("Box_",(0, 4-10, 1.0), BOX_DEFAULT_SIZE),
    ("Box_",(0, 8-10, 1.0), BOX_DEFAULT_SIZE),
    ("Box_",(0, 12-10, 1.0), BOX_DEFAULT_SIZE),
    ("Box_",(0, 16-10, 1.0), BOX_DEFAULT_SIZE),
    ("Box_",(0-10, 0, 1.0), BOX_DEFAULT_SIZE),
    ("Box_",(4-10, 0, 1.0), BOX_DEFAULT_SIZE),
    ("Box_",(8-10, 0, 1.0), BOX_DEFAULT_SIZE),
    ("Box_",(12-10, 0, 1.0), BOX_DEFAULT_SIZE),
    ("Box_",(16-10, 0, 1.0), BOX_DEFAULT_SIZE),
]


def _position_to_tuple(position):
    """Convert a JSON position value into a Blender-friendly coordinate tuple."""
    if len(position) != 3:
        raise ValueError("Each cube position must contain exactly three coordinates.")
    return tuple(float(coordinate) for coordinate in position)


def load_box_configs(input_path=None):
    """Load cube positions from a JSON input file or fall back to the built-in layout."""
    if input_path is None:
        return BOX_CONFIGS

    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
    count = payload.get("count")

    if "boxes" in payload:
        boxes = payload["boxes"]
        if count is not None and count != len(boxes):
            raise ValueError("Cube count does not match the number of boxes in the input file.")
        return [
            (
                box.get("name", f"Box_{index}"),
                _position_to_tuple(box["position"]),
                float(box.get("size", BOX_DEFAULT_SIZE)),
            )
            for index, box in enumerate(boxes, start=1)
        ]

    positions = payload.get("positions")
    if positions is None:
        raise ValueError("Cube input JSON must define either 'positions' or 'boxes'.")
    if count is not None and count != len(positions):
        raise ValueError("Cube count does not match the number of positions in the input file.")

    return [
        (f"Box_{index}", _position_to_tuple(position), BOX_DEFAULT_SIZE)
        for index, position in enumerate(positions, start=1)
    ]


def create_floor_geometry(size=100.0):
    """Return vertices and faces for a square floor plane."""
    half = size / 2.0
    verts = [
        (-half, -half, -0.00001),
        (half, -half, -0.00001),
        (half, half, -0.00001),
        (-half, half, -0.00001),
    ]
    faces = [(0, 1, 2, 3)]
    return verts, faces


def create_box_geometry(size):
    """Return vertices and faces for a cube centered at the origin with the given edge length."""
    radius = size / 2.0
    verts = [
        (-radius, -radius, -radius),
        (radius, -radius, -radius),
        (radius, radius, -radius),
        (-radius, radius, -radius),
        (-radius, -radius, radius),
        (radius, -radius, radius),
        (radius, radius, radius),
        (-radius, radius, radius),
    ]
    faces = [
        (0, 1, 2, 3),
        (7, 6, 5, 4),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ]
    return verts, faces
