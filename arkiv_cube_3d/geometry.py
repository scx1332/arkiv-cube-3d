import os
from dataclasses import dataclass
from typing import TypeAlias

from Tools.scripts.fixnotice import process

"""Pure geometry helpers for Blender mesh construction."""


# --- Type Definitions ---
Color: TypeAlias = tuple[float, float, float, float]
Position: TypeAlias = tuple[float, float, float]
Dimensions: TypeAlias = tuple[float, float, float]
InputPixel: TypeAlias = tuple[Color, float]

# --- Constants ---
BOX_SPACING_BASE = 19.8
BOX_SCALE = 0.92
BOX_HEIGHT_MULTIPLIER = 1.0
BOX_OVER_FLOOR_OFFSET_MULT = 0.2
BOX_UNDER_FLOOR_OFFSET_MULT = 2.0

@dataclass
class BoxConfig:
    """Configuration for a generated 3D box."""
    name: str
    position: Position
    dimensions: Dimensions
    color: Color


def create_box_configs(pixel_grid: list[list[InputPixel]]) -> list[BoxConfig]:
    """Generates a grid of box configurations based on pixel height and color data."""
    # Calculate the starting coordinate to center the grid at (0, 0)

    grid_height = len(pixel_grid)
    grid_width = len(pixel_grid[0])

    box_spacing = BOX_SPACING_BASE / max(grid_height, grid_width)
    box_size = box_spacing * BOX_SCALE

    grid_origin_x = -(grid_width - 1) / 2.0 * box_spacing
    grid_origin_y = -(grid_height - 1) / 2.0 * box_spacing

    box_configs: list[BoxConfig] = []
    box_number = 0

    color_intensity = 0.4

    full_intensity_height = 3.0

    height_percentage = float(os.getenv("HEIGHT_PERCENTAGE", "100.0")) / 100.0
    height_percentage_limit = 0.15

    move_x_b = float(os.getenv("MOVE_X_PERCENTAGE", "0.0")) / 100.0

    for pixel_x in range(len(pixel_grid[0])):
        for pixel_y in range(len(pixel_grid)):
            box_number += 1


            color, height_intensity = pixel_grid[pixel_y][pixel_x]
            move_x = 0
            if height_intensity > 0:
                height_intensity = 1.0
                move_x = move_x_b

            if height_percentage > height_percentage_limit:
                color_intensity = 1.0
            else:
                color_intensity = (height_percentage / height_percentage_limit) * 1.0

            # blend color with white based on intensity to avoid pure black
            # blended_color = tuple(
            #     color_intensity * c + (1 - color_intensity) * 1.0 for c in color[:3]
            # ) + (color[3],)  # Preserve original alpha
            # color = blended_color

            # Calculate 3D spatial properties
            box_height = height_intensity * height_percentage
            pos_base_x = pixel_x * box_spacing + grid_origin_x
            pos_x = pixel_x * box_spacing + grid_origin_x
            pos_y = pixel_y * box_spacing + grid_origin_y
            pos_z = box_height * box_spacing + BOX_OVER_FLOOR_OFFSET_MULT * box_spacing


            if os.getenv("OVERRIDE_WHITE"):
                color = (1.0, 1.0, 1.0, 1.0)

            # Create and append the typed configuration object
            box_configs.append(
                BoxConfig(
                    name=f"Box {box_number}",
                    position=(pos_x + move_x * box_spacing, pos_y, pos_z),
                    dimensions=(box_size, box_size, box_spacing),
                    color=color,
                )
            )
            box_number += 1
            box_configs.append(
                BoxConfig(
                    name=f"Box {box_number}",
                    position=(pos_x + move_x_b * box_spacing, pos_y, pos_z - box_spacing),
                    dimensions=(box_size, box_size, box_spacing),
                    color=(1.0, 1.0, 1.0, 1.0),
                )
            )

    return box_configs

def create_floor_geometry(size=20.0):
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


from typing import List, Tuple

def create_box_geometry(
        dimensions: Tuple[float, float, float]
) -> Tuple[List[Tuple[float, float, float]], List[Tuple[int, int, int, int]]]:
    """
    Creates a rectangular prism based on a (width, height, depth) tuple.

    Args:
        dimensions: A tuple (x_size, y_size, z_size)

    Returns:
        verts: List of (x, y, z) coordinates
        faces: List of vertex index quadruplets
    """
    # Unpack the dimensions tuple
    w, h, d = dimensions

    # Calculate half-extents to center at (0, 0, 0)
    x, y, z = w / 2.0, h / 2.0, d / 2.0

    # Vertices: 8 corners of the box
    verts: List[Tuple[float, float, float]] = [
        (-x, -y, -z), # 0
        ( x, -y, -z), # 1
        ( x,  y, -z), # 2
        (-x,  y, -z), # 3
        (-x, -y,  z), # 4
        ( x, -y,  z), # 5
        ( x,  y,  z), # 6
        (-x,  y,  z), # 7
    ]

    # Faces: Defined by vertex indices
    # Winding order: Counter-clockwise when viewed from outside
    faces: List[Tuple[int, int, int, int]] = [
        (0, 3, 2, 1), # Bottom (-Z)
        (4, 5, 6, 7), # Top (+Z)
        (0, 1, 5, 4), # Front (-Y)
        (1, 2, 6, 5), # Right (+X)
        (2, 3, 7, 6), # Back (+Y)
        (3, 0, 4, 7), # Left (-X)
    ]

    return verts, faces

# Example usage:
# size = (10.0, 5.0, 2.0)
# vertices, faces = create_box_geometry(size)
