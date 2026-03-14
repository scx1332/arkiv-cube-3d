"""Pure geometry helpers for Blender mesh construction."""



def create_box_configs(height):
    print(height)
    COUNT = 31
    BOX_SIZE = 0.55
    BOX_REAL_SIZE_MULTIPLIER = 0.95
    glob_x = -COUNT / 2 * BOX_SIZE + 0.5 * BOX_SIZE
    glob_y = -COUNT / 2 * BOX_SIZE + 0.5 * BOX_SIZE
    arr = []
    box_no = 0
    for i in range(0, COUNT):
        for j in range(0, COUNT):
            #z = 5 - 0.1 * ((i - COUNT/2) * (i - COUNT/2) + (j - COUNT/2) * (j - COUNT/2))
            #if z < 0:
            #    z = 0
            if i % 2 == 1 and j % 2 == 1 and i > 4 and j > 4 and i < COUNT - 4 and j < COUNT - 4:
                arr_x = int(i / 2 - 2)
                arr_y = int(j / 2 - 2)

                z = 1.3 * (1.0 - height[arr_y][arr_x])
                if z > 0.1:
                    color = (0.8, 0.35, 0.0, 1.0)
                else:
                    color = (1.0, 1.0, 1.0, 1.0)
            else:
                z = 0
                color = (1.0, 1.0, 1.0, 1.0)


            box_no += 1
            arr.append((f"Box {box_no}", (i  * BOX_SIZE + glob_x, j * BOX_SIZE + glob_y, z * BOX_SIZE), BOX_SIZE * BOX_REAL_SIZE_MULTIPLIER, color))
    return arr


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
