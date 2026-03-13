import unittest

from arkiv_cube_3d.geometry import BOX_CONFIGS, create_box_geometry, create_floor_geometry


class GeometryTests(unittest.TestCase):
    def test_create_floor_geometry_returns_plane_vertices_and_face(self):
        verts, faces = create_floor_geometry()

        self.assertEqual(
            verts,
            [
                (-50.0, -50.0, 0.0),
                (50.0, -50.0, 0.0),
                (50.0, 50.0, 0.0),
                (-50.0, 50.0, 0.0),
            ],
        )
        self.assertEqual(faces, [(0, 1, 2, 3)])

    def test_create_box_geometry_returns_cube_vertices_and_faces(self):
        verts, faces = create_box_geometry(1.9)

        self.assertEqual(
            verts,
            [
                (-1.0, -1.0, -1.0),
                (1.0, -1.0, -1.0),
                (1.0, 1.0, -1.0),
                (-1.0, 1.0, -1.0),
                (-1.0, -1.0, 1.0),
                (1.0, -1.0, 1.0),
                (1.0, 1.0, 1.0),
                (-1.0, 1.0, 1.0),
            ],
        )
        self.assertEqual(
            faces,
            [
                (0, 1, 2, 3),
                (7, 6, 5, 4),
                (0, 1, 5, 4),
                (1, 2, 6, 5),
                (2, 3, 7, 6),
                (3, 0, 4, 7),
            ],
        )

    def test_box_configs_define_five_boxes(self):
        self.assertEqual(len(BOX_CONFIGS), 5)
