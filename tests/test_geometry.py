import json
from pathlib import Path
import tempfile
import unittest

from arkiv_cube_3d.geometry import BOX_CONFIGS, BOX_DEFAULT_SIZE, create_box_geometry, create_floor_geometry, load_box_configs


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

    def test_load_box_configs_reads_positions_and_count_from_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "cubes.json"
            input_path.write_text(
                json.dumps({"count": 2, "positions": [[1, 2, 3], [4.5, 5.5, 6.5]]}),
                encoding="utf-8",
            )

            self.assertEqual(
                load_box_configs(input_path),
                [
                    ("Box_1", (1.0, 2.0, 3.0), BOX_DEFAULT_SIZE),
                    ("Box_2", (4.5, 5.5, 6.5), BOX_DEFAULT_SIZE),
                ],
            )

    def test_load_box_configs_rejects_mismatched_count(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "cubes.json"
            input_path.write_text(json.dumps({"count": 2, "positions": [[1, 2, 3]]}), encoding="utf-8")

            with self.assertRaises(ValueError):
                load_box_configs(input_path)
