"""Pure geometry helpers for Blender mesh construction."""


BOX_GRID_COUNT = 31
BOX_GRID_MARGIN = 4
BOX_SPACING = 0.55
BOX_SCALE = 0.95
BOX_HEIGHT_MULTIPLIER = 1.3
DEFAULT_BOX_COLOR = (1.0, 1.0, 1.0, 1.0)


def create_box_configs(pixel_grid):
    grid_origin_x = -BOX_GRID_COUNT / 2 * BOX_SPACING + 0.5 * BOX_SPACING
    grid_origin_y = -BOX_GRID_COUNT / 2 * BOX_SPACING + 0.5 * BOX_SPACING
    box_configs = []
    box_number = 0

    for column_index in range(BOX_GRID_COUNT):
        for row_index in range(BOX_GRID_COUNT):
            pixel_column = column_index - BOX_GRID_MARGIN
            pixel_row = row_index - BOX_GRID_MARGIN

            try:
                color, height_intensity = pixel_grid[pixel_row][pixel_column]
            except (IndexError, TypeError):
                color, height_intensity = DEFAULT_BOX_COLOR, 0.0

            box_height = BOX_HEIGHT_MULTIPLIER * height_intensity
            box_number += 1
            box_configs.append(
                (
                    f"Box {box_number}",
                    (
                        column_index * BOX_SPACING + grid_origin_x,
                        row_index * BOX_SPACING + grid_origin_y,
                        box_height * BOX_SPACING,
                    ),
                    BOX_SPACING * BOX_SCALE,
                    color,
                )
            )

    return box_configs


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
    height = 2
    verts = [
        (-radius, -radius, -height),
        (radius, -radius, -height),
        (radius, radius, -height),
        (-radius, radius, -height),
        (-radius, -radius, height),
        (radius, -radius, height),
        (radius, radius, height),
        (-radius, radius, height),
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
