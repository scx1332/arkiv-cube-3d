import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from arkiv_cube_3d import geometry, render_cube


class ImageGeometryTests(unittest.TestCase):
    def test_create_box_configs_uses_pixel_color_and_height_intensity(self):
        height_intensity = 0.75
        box_configs = geometry.create_box_configs([[((0.2, 0.4, 0.6, 1.0), height_intensity)]])

        self.assertEqual(len(box_configs), 31 * 31)
        self.assertEqual(box_configs[0][3], (1.0, 1.0, 1.0, 1.0))
        self.assertEqual(box_configs[0][1][2], 0.0)

        image_box = box_configs[4 * 31 + 4]
        self.assertEqual(image_box[3], (0.2, 0.4, 0.6, 1.0))
        self.assertAlmostEqual(image_box[1][2], geometry.BOX_HEIGHT_MULTIPLIER * height_intensity * geometry.BOX_SPACING)

    def test_load_image_heightmap_returns_colors_and_inverted_brightness(self):
        total_pixels = render_cube.HEIGHTMAP_IMAGE_SIZE * render_cube.HEIGHTMAP_IMAGE_SIZE
        pixels = [0.5, 0.5, 0.5, 1.0] * total_pixels

        pixels[0:4] = [0.0, 0.0, 0.0, 1.0]
        pixels[4:8] = [1.0, 1.0, 1.0, 0.25]
        pixels[8:12] = [0.25, 0.5, 0.75, 0.5]

        class Image:
            size = (render_cube.HEIGHTMAP_IMAGE_SIZE, render_cube.HEIGHTMAP_IMAGE_SIZE)

            def __init__(self, rgba_pixels):
                self.pixels = rgba_pixels

        class Images(list):
            def __init__(self, image):
                super().__init__([image])
                self._image = image
                self.loaded_filepaths = []
                self.removed = []

            def load(self, *, filepath):
                self.loaded_filepaths.append(filepath)
                return self._image

            def remove(self, image, do_unlink=True):
                self.removed.append((image, do_unlink))

        image = Image(pixels)
        images = Images(image)
        blender = type("Blender", (), {"data": type("Data", (), {"images": images})()})()

        with patch.object(render_cube, "bpy", blender):
            pixel_grid = render_cube.load_image_heightmap("example.png")

        self.assertEqual(len(pixel_grid), render_cube.HEIGHTMAP_IMAGE_SIZE)
        self.assertEqual(len(pixel_grid[0]), render_cube.HEIGHTMAP_IMAGE_SIZE)
        self.assertEqual(pixel_grid[0][0], ((0.0, 0.0, 0.0, 1.0), 1.0))
        self.assertEqual(pixel_grid[0][1][0], (1.0, 1.0, 1.0, 0.25))
        self.assertAlmostEqual(pixel_grid[0][1][1], 1.0 - (1.0 + 1.0 + 1.0) / 3.0)
        self.assertEqual(pixel_grid[0][2][0], (0.25, 0.5, 0.75, 0.5))
        self.assertAlmostEqual(pixel_grid[0][2][1], 1.0 - (0.25 + 0.5 + 0.75) / 3.0)
        self.assertEqual(images.loaded_filepaths, [str(Path("example.png").resolve())])
        self.assertEqual(images.removed, [(image, True)])

    def test_add_soft_border_rgba_extends_image_with_blended_border(self):
        width, height, rows = render_cube.add_soft_border_rgba(
            1,
            1,
            [bytearray([10, 20, 30, 255])],
            border_width=2,
            border_color=(245, 245, 245, 255),
        )

        self.assertEqual((width, height), (5, 5))
        self.assertEqual(list(rows[2][2 * 4 : 2 * 4 + 4]), [10, 20, 30, 255])
        self.assertEqual(list(rows[0][0:4]), [245, 245, 245, 255])

        edge_pixel = list(rows[2][1 * 4 : 1 * 4 + 4])
        self.assertGreater(edge_pixel[0], 10)
        self.assertLess(edge_pixel[0], 245)
        self.assertGreater(edge_pixel[1], 20)
        self.assertLess(edge_pixel[1], 245)
        self.assertGreater(edge_pixel[2], 30)
        self.assertLess(edge_pixel[2], 245)

    def test_postprocess_render_output_rewrites_png_with_soft_border(self):
        source_rows = [
            bytearray([10, 20, 30, 255, 40, 50, 60, 255]),
            bytearray([70, 80, 90, 255, 100, 110, 120, 255]),
        ]

        with TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "render.png"
            render_cube._write_png_rgba(image_path, 2, 2, source_rows)

            render_cube.postprocess_render_output(image_path, border_width=1, border_color=(0.96, 0.96, 0.96, 1.0))
            width, height, processed_rows = render_cube._read_png_rgba(image_path)

        self.assertEqual((width, height), (4, 4))
        self.assertEqual(list(processed_rows[1][1 * 4 : 1 * 4 + 4]), [10, 20, 30, 255])
        self.assertEqual(list(processed_rows[0][0:4]), [245, 245, 245, 255])


if __name__ == "__main__":
    unittest.main()
