import unittest
from pathlib import Path
from unittest.mock import patch

from arkiv_cube_3d import geometry, render_cube


class ImageGeometryTests(unittest.TestCase):
    def test_create_box_configs_uses_pixel_color_and_height_intensity(self):
        box_configs = geometry.create_box_configs([[((0.2, 0.4, 0.6, 1.0), 0.75)]])

        self.assertEqual(len(box_configs), 31 * 31)
        self.assertEqual(box_configs[0][3], (1.0, 1.0, 1.0, 1.0))
        self.assertEqual(box_configs[0][1][2], 0.0)

        image_box = box_configs[4 * 31 + 4]
        self.assertEqual(image_box[3], (0.2, 0.4, 0.6, 1.0))
        self.assertAlmostEqual(image_box[1][2], 1.3 * 0.75 * 0.55)

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
        self.assertEqual(pixel_grid[0][1], ((1.0, 1.0, 1.0, 0.25), 0.0))
        self.assertEqual(pixel_grid[0][2][0], (0.25, 0.5, 0.75, 0.5))
        self.assertAlmostEqual(pixel_grid[0][2][1], 0.5)
        self.assertEqual(images.loaded_filepaths, [str(Path("example.png").resolve())])
        self.assertEqual(images.removed, [(image, True)])


if __name__ == "__main__":
    unittest.main()
