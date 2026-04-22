from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from core.compositor import (
    BOX_PADDING,
    batch_composite,
    build_composite,
    flatten_on_white,
    get_layout_preset,
    list_products,
    load_layer,
    remove_edge_connected_near_white,
)


def composite_pixel(base_rgba: tuple[int, int, int, int], top_rgba: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    base = Image.new("RGBA", (1, 1), base_rgba)
    top = Image.new("RGBA", (1, 1), top_rgba)
    return Image.alpha_composite(base, top).getpixel((0, 0))


class CompositorTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def make_image(self, name: str, size: tuple[int, int], color: tuple[int, int, int, int]) -> Path:
        path = self.tmp_path / name
        Image.new("RGBA", size, color).save(path)
        return path

    def make_product_with_transparent_border(self, name: str) -> Path:
        path = self.tmp_path / name
        image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((25, 25, 74, 74), fill=(0, 255, 0, 255))
        image.save(path)
        return path

    def make_white_background_foreground(self, name: str) -> Path:
        path = self.tmp_path / name
        image = Image.new("RGBA", (100, 100), (255, 255, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.rectangle((20, 20, 79, 79), fill=(255, 0, 0, 255))
        image.save(path)
        return path

    def test_build_composite_with_background_only(self):
        preset = get_layout_preset("1:1")
        product_path = self.make_image("product.png", (100, 100), (0, 255, 0, 255))
        background = Image.new("RGBA", preset.canvas_size, (255, 0, 0, 255))

        result = build_composite("1:1", product_path, background=background)

        left, top, right, bottom = preset.safe_box
        center = ((left + right) // 2, (top + bottom) // 2)
        self.assertEqual(result.size, preset.canvas_size)
        self.assertEqual(result.getpixel((5, 5)), (255, 0, 0, 255))
        self.assertEqual(result.getpixel(center), (0, 255, 0, 255))

    def test_build_composite_with_foreground_only(self):
        preset = get_layout_preset("1:1")
        product_path = self.make_image("product.png", (100, 100), (0, 255, 0, 255))
        foreground = Image.new("RGBA", preset.canvas_size, (0, 0, 255, 128))

        result = build_composite("1:1", product_path, foreground=foreground)

        left, top, right, bottom = preset.safe_box
        center = ((left + right) // 2, (top + bottom) // 2)
        self.assertEqual(
            result.getpixel((5, 5)),
            composite_pixel((255, 255, 255, 255), (0, 0, 255, 128)),
        )
        self.assertEqual(
            result.getpixel(center),
            composite_pixel((0, 255, 0, 255), (0, 0, 255, 128)),
        )

    def test_build_composite_with_background_and_foreground(self):
        preset = get_layout_preset("1:1")
        product_path = self.make_image("product.png", (100, 100), (0, 255, 0, 255))
        background = Image.new("RGBA", preset.canvas_size, (255, 0, 0, 255))
        foreground = Image.new("RGBA", preset.canvas_size, (0, 0, 255, 128))

        result = build_composite(
            "1:1",
            product_path,
            background=background,
            foreground=foreground,
        )

        left, top, right, bottom = preset.safe_box
        center = ((left + right) // 2, (top + bottom) // 2)
        self.assertEqual(
            result.getpixel((5, 5)),
            composite_pixel((255, 0, 0, 255), (0, 0, 255, 128)),
        )
        self.assertEqual(
            result.getpixel(center),
            composite_pixel((0, 255, 0, 255), (0, 0, 255, 128)),
        )

    def test_load_layer_rejects_wrong_ratio(self):
        background_path = self.make_image("wrong_ratio.png", (100, 50), (255, 0, 0, 255))

        with self.assertRaisesRegex(ValueError, "後景底圖比例不符合 1:1"):
            load_layer(background_path, "1:1", "後景底圖")

    def test_remove_edge_connected_near_white_preserves_internal_white(self):
        image = Image.new("RGBA", (7, 7), (255, 255, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.rectangle((2, 2, 4, 4), fill=(0, 0, 0, 255))
        draw.point((3, 3), fill=(255, 255, 255, 255))

        processed = remove_edge_connected_near_white(image)

        self.assertEqual(processed.getpixel((0, 0)), (255, 255, 255, 0))
        self.assertEqual(processed.getpixel((3, 3)), (255, 255, 255, 255))

    def test_load_layer_removes_white_background_for_foreground(self):
        foreground_path = self.make_white_background_foreground("foreground_white.png")

        foreground = load_layer(foreground_path, "1:1", "前景套框")

        assert foreground is not None
        self.assertEqual(foreground.getpixel((5, 5))[3], 0)
        self.assertEqual(foreground.getpixel((540, 540)), (255, 0, 0, 255))

    def test_list_products_accepts_uppercase_extensions(self):
        input_dir = self.tmp_path / "products"
        input_dir.mkdir()
        Image.new("RGBA", (20, 20), (255, 0, 0, 255)).save(input_dir / "A.PNG")
        Image.new("RGBA", (20, 20), (0, 255, 0, 255)).save(input_dir / "B.WEBP")

        products = list_products(input_dir)

        self.assertEqual([path.name for path in products], ["A.PNG", "B.WEBP"])

    def test_transparent_product_is_cropped_before_scaling(self):
        preset = get_layout_preset("1:1")
        product_path = self.make_product_with_transparent_border("bordered_product.png")
        background = Image.new("RGBA", preset.canvas_size, (255, 255, 255, 255))

        result = build_composite("1:1", product_path, background=background)

        left, top, right, bottom = preset.safe_box
        sample_x = left + BOX_PADDING + 10
        sample_y = (top + bottom) // 2
        self.assertEqual(result.getpixel((sample_x, sample_y)), (0, 255, 0, 255))

    def test_flatten_on_white_removes_transparent_output(self):
        image = Image.new("RGBA", (4, 4), (0, 0, 255, 128))

        flattened = flatten_on_white(image)

        self.assertEqual(
            flattened.getpixel((0, 0)),
            composite_pixel((255, 255, 255, 255), (0, 0, 255, 128)),
        )

    def test_build_composite_flattens_transparent_background_to_white(self):
        preset = get_layout_preset("1:1")
        product_path = self.make_image("product.png", (100, 100), (0, 255, 0, 255))
        background = Image.new("RGBA", preset.canvas_size, (0, 0, 0, 0))

        result = build_composite("1:1", product_path, background=background)

        left, top, right, bottom = preset.safe_box
        center = ((left + right) // 2, (top + bottom) // 2)
        self.assertEqual(result.getpixel((5, 5)), (255, 255, 255, 255))
        self.assertEqual(result.getpixel(center), (0, 255, 0, 255))

    def test_batch_composite_normalizes_same_ratio_layers(self):
        preset = get_layout_preset("9:16")
        input_dir = self.tmp_path / "input"
        output_dir = self.tmp_path / "output"
        input_dir.mkdir()

        product_path = input_dir / "product.png"
        Image.new("RGBA", (100, 100), (0, 255, 0, 255)).save(product_path)

        background_path = self.make_image("background.png", (540, 960), (255, 0, 0, 255))
        foreground_path = self.make_image("foreground.png", (1080, 1920), (0, 0, 255, 128))

        progress = list(
            batch_composite(
                "9:16",
                input_dir,
                output_dir,
                background_path=background_path,
                foreground_path=foreground_path,
            )
        )

        self.assertEqual(len(progress), 1)
        output_path = progress[0][2]
        with Image.open(output_path) as result:
            left, top, right, bottom = preset.safe_box
            center = ((left + right) // 2, (top + bottom) // 2)
            self.assertEqual(result.size, preset.canvas_size)
            self.assertEqual(
                result.getpixel((5, 5)),
                composite_pixel((255, 0, 0, 255), (0, 0, 255, 128)),
            )
            self.assertEqual(
                result.getpixel(center),
                composite_pixel((0, 255, 0, 255), (0, 0, 255, 128)),
            )


if __name__ == "__main__":
    unittest.main()
