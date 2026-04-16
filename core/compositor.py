from __future__ import annotations

from pathlib import Path

from PIL import Image

SAFE_BOX = (38, 145, 638, 850)
BOX_PADDING = 20
OUTPUT_SUFFIX = "_套框"
SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def fit_size(size: tuple[int, int], max_size: tuple[int, int]) -> tuple[int, int]:
    width, height = size
    max_width, max_height = max_size
    scale = min(max_width / width, max_height / height)
    return max(1, round(width * scale)), max(1, round(height * scale))


def crop_visible_area(image: Image.Image) -> Image.Image:
    if image.mode != "RGBA":
        return image
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        return image
    return image.crop(bbox)


def build_composite(
    frame: Image.Image,
    product_path: Path,
    offset_x: int = 0,
    offset_y: int = 0,
    scale: float = 1.0,
) -> Image.Image:
    canvas = frame.copy().convert("RGBA")
    product = crop_visible_area(Image.open(product_path).convert("RGBA"))

    left, top, right, bottom = SAFE_BOX
    max_width = right - left - BOX_PADDING * 2
    max_height = bottom - top - BOX_PADDING * 2

    fit_w, fit_h = fit_size(product.size, (max_width, max_height))
    scaled_w = max(1, round(fit_w * scale))
    scaled_h = max(1, round(fit_h * scale))
    resized = product.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)

    paste_x = left + (right - left - resized.width) // 2 + offset_x
    paste_y = top + (bottom - top - resized.height) // 2 + offset_y

    # Use overlay approach so the product can extend beyond canvas bounds safely.
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    overlay.paste(resized, (paste_x, paste_y), resized)
    return Image.alpha_composite(canvas, overlay)


def list_products(input_dir: Path) -> list[Path]:
    files = []
    for ext in SUPPORTED_EXTENSIONS:
        files.extend(input_dir.glob(f"*{ext}"))
    return sorted(set(files))


def batch_composite(
    frame_path: Path,
    input_dir: Path,
    output_dir: Path,
    offset_x: int = 0,
    offset_y: int = 0,
    scale: float = 1.0,
):
    """Generator that yields (current, total, output_path) after each image."""
    frame = Image.open(frame_path).convert("RGBA")
    products = list_products(input_dir)
    total = len(products)
    output_dir.mkdir(parents=True, exist_ok=True)
    for i, product_path in enumerate(products):
        result = build_composite(frame, product_path, offset_x, offset_y, scale)
        out = output_dir / f"{product_path.stem}{OUTPUT_SUFFIX}.png"
        result.save(out)
        yield i + 1, total, out
