"""Pure geometry helpers for Blender mesh construction."""


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
