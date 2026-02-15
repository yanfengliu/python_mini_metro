import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from ui.viewport import get_viewport_transform


class TestViewport(unittest.TestCase):
    def test_get_viewport_transform_letterboxes_height(self):
        transform = get_viewport_transform(
            window_width=1280,
            window_height=1024,
            virtual_width=1920,
            virtual_height=1080,
        )
        self.assertEqual(transform.width, 1280)
        self.assertEqual(transform.height, 720)
        self.assertEqual(transform.offset_x, 0)
        self.assertEqual(transform.offset_y, (1024 - 720) // 2)

    def test_map_window_to_virtual_maps_center(self):
        transform = get_viewport_transform(
            window_width=2560,
            window_height=1440,
            virtual_width=1920,
            virtual_height=1080,
        )
        mapped = transform.map_window_to_virtual(1280, 720, 1920, 1080)
        self.assertEqual(mapped, (960, 540))

    def test_map_window_to_virtual_returns_none_outside_viewport(self):
        transform = get_viewport_transform(
            window_width=1000,
            window_height=1000,
            virtual_width=1920,
            virtual_height=1080,
        )
        self.assertIsNone(transform.map_window_to_virtual(10, 10, 1920, 1080))


if __name__ == "__main__":
    unittest.main()
