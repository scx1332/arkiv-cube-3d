"""Pure geometry helpers for Blender mesh construction."""

BOX_CONFIGS = [
    ("Box_Center", (0, 0, 2.0), 2.0),
    ("Box_East", (5, 0, 2.0), 2.0),
    ("Box_North", (0, 5, 2.0), 2.0),
    ("Box_West", (-5, 0, 2.0), 2.0),
    ("Box_South", (0, -5, 2.0), 2.0),
]


def create_floor_geometry(size=100.0):
    """Return vertices and faces for a square floor plane."""
    half = size / 2.0
    verts = [
        (-half, -half, 0.0),
        (half, -half, 0.0),
        (half, half, 0.0),
        (-half, half, 0.0),
    ]
    faces = [(0, 1, 2, 3)]
    return verts, faces


def create_box_geometry(size):
    """Return vertices and faces for a cube centered at the origin."""
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
