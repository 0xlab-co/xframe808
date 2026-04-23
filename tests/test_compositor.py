from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from core.compositor import (
    BOX_PADDING,
    IDENTITY_TRANSFORM,
    LayerTransform,
    batch_composite,
    build_composite,
    build_composite_frame,
    build_layer_preview,
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

    def test_load_layer_accepts_crop_box_from_wrong_ratio_image(self):
        background_path = self.make_image("wide.png", (200, 100), (255, 0, 0, 255))

        background = load_layer(background_path, "1:1", "後景底圖", crop_box=(50, 0, 150, 100))

        assert background is not None
        self.assertEqual(background.size, (1080, 1080))
        self.assertEqual(background.getpixel((12, 12)), (255, 0, 0, 255))

    def test_build_composite_frame_matches_build_composite(self):
        preset = get_layout_preset("1:1")
        product_path = self.make_product_with_transparent_border("product.png")
        background = Image.new("RGBA", preset.canvas_size, (255, 0, 0, 255))
        foreground = Image.new("RGBA", preset.canvas_size, (0, 0, 255, 64))

        via_path = build_composite(
            "1:1", product_path, background=background, foreground=foreground
        )
        with Image.open(product_path) as src:
            product_image = src.convert("RGBA")
        via_image = build_composite_frame(
            "1:1", product_image, background=background, foreground=foreground
        )

        self.assertEqual(via_path.size, via_image.size)
        self.assertEqual(list(via_path.getdata()), list(via_image.getdata()))

    def test_list_products_includes_video_extensions(self):
        input_dir = self.tmp_path / "mixed_products"
        input_dir.mkdir()
        (input_dir / "a.mp4").touch()
        (input_dir / "b.MOV").touch()
        (input_dir / "c.webm").touch()
        Image.new("RGBA", (20, 20), (255, 0, 0, 255)).save(input_dir / "d.png")

        names = sorted(path.name for path in list_products(input_dir))

        self.assertEqual(names, ["a.mp4", "b.MOV", "c.webm", "d.png"])

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

    def test_build_layer_preview_flattens_layers_without_product(self):
        preset = get_layout_preset("1:1")
        foreground = Image.new("RGBA", preset.canvas_size, (0, 0, 255, 128))

        result = build_layer_preview("1:1", foreground=foreground)

        self.assertEqual(
            result.getpixel((8, 8)),
            composite_pixel((255, 255, 255, 255), (0, 0, 255, 128)),
        )

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

    def test_batch_composite_accepts_crop_box_for_wrong_ratio_background(self):
        preset = get_layout_preset("1:1")
        input_dir = self.tmp_path / "input_crop"
        output_dir = self.tmp_path / "output_crop"
        input_dir.mkdir()

        product_path = input_dir / "product.png"
        Image.new("RGBA", (100, 100), (0, 255, 0, 255)).save(product_path)
        background_path = self.make_image("wide_bg.png", (200, 100), (255, 0, 0, 255))

        progress = list(
            batch_composite(
                "1:1",
                input_dir,
                output_dir,
                background_path=background_path,
                background_crop_box=(50, 0, 150, 100),
            )
        )

        self.assertEqual(len(progress), 1)
        output_path = progress[0][2]
        with Image.open(output_path) as result:
            left, top, right, bottom = preset.safe_box
            center = ((left + right) // 2, (top + bottom) // 2)
            self.assertEqual(result.size, preset.canvas_size)
            self.assertEqual(result.getpixel((5, 5)), (255, 0, 0, 255))
            self.assertEqual(result.getpixel(center), (0, 255, 0, 255))


    def test_layer_transform_identity_matches_legacy(self):
        preset = get_layout_preset("1:1")
        product_path = self.make_product_with_transparent_border("product.png")
        background = Image.new("RGBA", preset.canvas_size, (255, 0, 0, 255))
        foreground = Image.new("RGBA", preset.canvas_size, (0, 0, 255, 64))

        legacy = build_composite(
            "1:1", product_path, background=background, foreground=foreground
        )
        with_identity = build_composite(
            "1:1",
            product_path,
            background=background,
            foreground=foreground,
            background_transform=IDENTITY_TRANSFORM,
            foreground_transform=IDENTITY_TRANSFORM,
            product_transform=IDENTITY_TRANSFORM,
        )
        self.assertEqual(list(legacy.getdata()), list(with_identity.getdata()))

    def test_background_transform_offsets_pixels(self):
        preset = get_layout_preset("1:1")
        product_path = self.make_image("product.png", (100, 100), (0, 255, 0, 255))
        background = Image.new("RGBA", preset.canvas_size, (255, 0, 0, 255))

        result = build_composite(
            "1:1",
            product_path,
            background=background,
            background_transform=LayerTransform(offset_x=100, offset_y=0, scale=1.0),
        )
        # The far-left edge, previously red, is revealed outside the shifted
        # bg → flattens to white. The original bg still shows past x=100.
        self.assertEqual(result.getpixel((5, 5)), (255, 255, 255, 255))
        self.assertEqual(result.getpixel((200, 5)), (255, 0, 0, 255))

    def test_foreground_transform_scale_half(self):
        preset = get_layout_preset("1:1")
        product_path = self.make_image("product.png", (100, 100), (0, 255, 0, 255))
        background = Image.new("RGBA", preset.canvas_size, (255, 0, 0, 255))
        # Fully opaque blue fg that normally covers the whole canvas.
        foreground = Image.new("RGBA", preset.canvas_size, (0, 0, 255, 255))

        result = build_composite(
            "1:1",
            product_path,
            background=background,
            foreground=foreground,
            foreground_transform=LayerTransform(scale=0.5),
        )
        # Outside the centered half-sized fg → bg red remains.
        self.assertEqual(result.getpixel((10, 10)), (255, 0, 0, 255))
        # Center is covered by the scaled-down fg → blue.
        cx = preset.canvas_size[0] // 2
        cy = preset.canvas_size[1] // 2
        self.assertEqual(result.getpixel((cx, cy)), (0, 0, 255, 255))

    def test_product_transforms_dict_is_per_path(self):
        preset = get_layout_preset("1:1")
        input_dir = self.tmp_path / "per_product_input"
        output_dir = self.tmp_path / "per_product_output"
        input_dir.mkdir()

        a_path = input_dir / "a.png"
        b_path = input_dir / "b.png"
        Image.new("RGBA", (100, 100), (0, 255, 0, 255)).save(a_path)
        Image.new("RGBA", (100, 100), (0, 255, 0, 255)).save(b_path)

        background_path = self.make_image(
            "white_bg.png", preset.canvas_size, (255, 255, 255, 255)
        )

        product_transforms = {
            a_path: LayerTransform(offset_x=200, offset_y=0, scale=1.0),
        }

        outputs = [
            entry[2]
            for entry in batch_composite(
                "1:1",
                input_dir,
                output_dir,
                background_path=background_path,
                product_transforms=product_transforms,
            )
        ]

        self.assertEqual(len(outputs), 2)
        by_name = {p.stem: p for p in outputs}

        mid_y = (preset.safe_box[1] + preset.safe_box[3]) // 2

        def first_green_x(img: Image.Image) -> int:
            for x in range(img.width):
                if img.getpixel((x, mid_y)) == (0, 255, 0, 255):
                    return x
            return -1

        with Image.open(by_name["a_套框"]) as img_a:
            a_left = first_green_x(img_a)
        with Image.open(by_name["b_套框"]) as img_b:
            b_left = first_green_x(img_b)

        self.assertGreaterEqual(b_left, 0)
        self.assertGreaterEqual(a_left, 0)
        self.assertEqual(a_left - b_left, 200)

    def test_product_transforms_missing_key_uses_identity(self):
        preset = get_layout_preset("1:1")
        input_dir = self.tmp_path / "identity_input"
        output_dir = self.tmp_path / "identity_output"
        input_dir.mkdir()
        product_path = input_dir / "p.png"
        Image.new("RGBA", (100, 100), (0, 255, 0, 255)).save(product_path)

        background_path = self.make_image(
            "red_bg.png", preset.canvas_size, (255, 0, 0, 255)
        )

        outputs = [
            entry[2]
            for entry in batch_composite(
                "1:1",
                input_dir,
                output_dir,
                background_path=background_path,
                product_transforms={},
            )
        ]
        self.assertEqual(len(outputs), 1)
        with Image.open(outputs[0]) as result:
            center = (
                (preset.safe_box[0] + preset.safe_box[2]) // 2,
                (preset.safe_box[1] + preset.safe_box[3]) // 2,
            )
            self.assertEqual(result.getpixel((5, 5)), (255, 0, 0, 255))
            self.assertEqual(result.getpixel(center), (0, 255, 0, 255))

    def test_build_layer_preview_supports_layer_transforms(self):
        preset = get_layout_preset("1:1")
        foreground = Image.new("RGBA", preset.canvas_size, (0, 0, 255, 255))
        background = Image.new("RGBA", preset.canvas_size, (255, 0, 0, 255))

        result = build_layer_preview(
            "1:1",
            background=background,
            foreground=foreground,
            foreground_transform=LayerTransform(scale=0.5),
        )
        # Outside the shrunken fg → red bg
        self.assertEqual(result.getpixel((8, 8)), (255, 0, 0, 255))
        cx = preset.canvas_size[0] // 2
        self.assertEqual(result.getpixel((cx, cx)), (0, 0, 255, 255))


if __name__ == "__main__":
    unittest.main()
