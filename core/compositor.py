from __future__ import annotations

from dataclasses import dataclass
from collections import deque
from pathlib import Path
from typing import Callable

from PIL import Image

from core.video import VIDEO_EXTENSIONS, is_video_file

LEGACY_CANVAS_SIZE = (1084, 1084)
LEGACY_SAFE_BOX = (38, 145, 638, 850)
BOX_PADDING = 20
OUTPUT_SUFFIX = "_套框"
SUPPORTED_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS + VIDEO_EXTENSIONS
ASPECT_RATIO_TOLERANCE = 0.005
NEAR_WHITE_THRESHOLD = 245
CropBox = tuple[int, int, int, int]
FrameProgressCallback = Callable[[int, int, str], None]
CancelCheckCallback = Callable[[], bool]


@dataclass(frozen=True)
class LayerTransform:
    offset_x: int = 0
    offset_y: int = 0
    scale: float = 1.0

    @property
    def is_identity(self) -> bool:
        return self.offset_x == 0 and self.offset_y == 0 and self.scale == 1.0


IDENTITY_TRANSFORM = LayerTransform()


@dataclass(frozen=True)
class LayoutPreset:
    preset_id: str
    canvas_size: tuple[int, int]
    safe_box: tuple[int, int, int, int]

    @property
    def aspect_ratio(self) -> float:
        width, height = self.canvas_size
        return width / height


def scale_box(
    box: tuple[int, int, int, int],
    from_size: tuple[int, int],
    to_size: tuple[int, int],
) -> tuple[int, int, int, int]:
    from_width, from_height = from_size
    to_width, to_height = to_size
    scale_x = to_width / from_width
    scale_y = to_height / from_height
    left, top, right, bottom = box
    return (
        round(left * scale_x),
        round(top * scale_y),
        round(right * scale_x),
        round(bottom * scale_y),
    )


def centered_box(
    canvas_size: tuple[int, int],
    horizontal_margin_ratio: float,
    vertical_margin_ratio: float,
) -> tuple[int, int, int, int]:
    width, height = canvas_size
    margin_x = round(width * horizontal_margin_ratio)
    margin_y = round(height * vertical_margin_ratio)
    return (
        margin_x,
        margin_y,
        width - margin_x,
        height - margin_y,
    )


PRESET_ORDER = ("1:1", "9:16", "16:9", "3:4")

LAYOUT_PRESETS: dict[str, LayoutPreset] = {
    "1:1": LayoutPreset(
        preset_id="1:1",
        canvas_size=(1080, 1080),
        safe_box=scale_box(LEGACY_SAFE_BOX, LEGACY_CANVAS_SIZE, (1080, 1080)),
    ),
    "9:16": LayoutPreset(
        preset_id="9:16",
        canvas_size=(1080, 1920),
        safe_box=centered_box((1080, 1920), 0.10, 0.14),
    ),
    "16:9": LayoutPreset(
        preset_id="16:9",
        canvas_size=(1920, 1080),
        safe_box=centered_box((1920, 1080), 0.11, 0.12),
    ),
    "3:4": LayoutPreset(
        preset_id="3:4",
        canvas_size=(1080, 1440),
        safe_box=centered_box((1080, 1440), 0.10, 0.13),
    ),
}


def get_layout_preset(preset_id: str) -> LayoutPreset:
    try:
        return LAYOUT_PRESETS[preset_id]
    except KeyError as exc:
        raise ValueError(f"不支援的輸出比例：{preset_id}") from exc


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


def apply_crop_box(image: Image.Image, crop_box: CropBox) -> Image.Image:
    width, height = image.size
    left, top, right, bottom = crop_box
    left = max(0, min(width - 1, int(round(left))))
    top = max(0, min(height - 1, int(round(top))))
    right = max(left + 1, min(width, int(round(right))))
    bottom = max(top + 1, min(height, int(round(bottom))))
    if right <= left or bottom <= top:
        raise ValueError("裁切範圍無效。")
    return image.crop((left, top, right, bottom))


def aspect_ratio_matches(
    size: tuple[int, int],
    preset: LayoutPreset,
    tolerance: float = ASPECT_RATIO_TOLERANCE,
) -> bool:
    width, height = size
    if width <= 0 or height <= 0:
        return False
    actual_ratio = width / height
    return abs(actual_ratio - preset.aspect_ratio) / preset.aspect_ratio <= tolerance


def validate_layer_image(image: Image.Image, preset: LayoutPreset, layer_name: str) -> None:
    if aspect_ratio_matches(image.size, preset):
        return
    width, height = image.size
    raise ValueError(
        f"{layer_name}比例不符合 {preset.preset_id}。"
        f" 目前尺寸為 {width}x{height}，請改用符合比例的圖片。"
    )


def normalize_layer(image: Image.Image, preset: LayoutPreset) -> Image.Image:
    return image.convert("RGBA").resize(preset.canvas_size, Image.Resampling.LANCZOS)


def is_near_white(pixel: tuple[int, int, int, int]) -> bool:
    r, g, b, a = pixel
    return a > 0 and r >= NEAR_WHITE_THRESHOLD and g >= NEAR_WHITE_THRESHOLD and b >= NEAR_WHITE_THRESHOLD


def remove_edge_connected_near_white(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    if width == 0 or height == 0:
        return rgba

    pixels = rgba.load()
    visited = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def try_visit(x: int, y: int) -> None:
        if not (0 <= x < width and 0 <= y < height):
            return
        idx = y * width + x
        if visited[idx]:
            return
        visited[idx] = 1
        if is_near_white(pixels[x, y]):
            queue.append((x, y))

    for x in range(width):
        try_visit(x, 0)
        try_visit(x, height - 1)
    for y in range(height):
        try_visit(0, y)
        try_visit(width - 1, y)

    while queue:
        x, y = queue.popleft()
        r, g, b, _ = pixels[x, y]
        pixels[x, y] = (r, g, b, 0)
        for dx, dy in (
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -1),
            (0, 1),
            (1, -1),
            (1, 0),
            (1, 1),
        ):
            try_visit(x + dx, y + dy)

    return rgba


def flatten_on_white(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    white_background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    return Image.alpha_composite(white_background, rgba)


def load_layer(
    path: Path | None,
    preset_id: str,
    layer_name: str,
    crop_box: CropBox | None = None,
) -> Image.Image | None:
    if path is None:
        return None
    preset = get_layout_preset(preset_id)
    with Image.open(path) as image:
        if crop_box is not None:
            image = apply_crop_box(image, crop_box)
        validate_layer_image(image, preset, layer_name)
        if layer_name == "前景套框":
            image = remove_edge_connected_near_white(image)
        return normalize_layer(image, preset)


def load_layers(
    preset_id: str,
    background_path: Path | None = None,
    foreground_path: Path | None = None,
    background_crop_box: CropBox | None = None,
    foreground_crop_box: CropBox | None = None,
) -> tuple[Image.Image | None, Image.Image | None]:
    if background_path is None and foreground_path is None:
        raise ValueError("請至少選擇前景套框或後景底圖。")

    background = load_layer(background_path, preset_id, "後景底圖", crop_box=background_crop_box)
    foreground = load_layer(foreground_path, preset_id, "前景套框", crop_box=foreground_crop_box)
    return background, foreground


def _place_product(
    preset: LayoutPreset,
    product_image: Image.Image,
    transform: LayerTransform = IDENTITY_TRANSFORM,
) -> tuple[Image.Image, tuple[int, int]]:
    product = crop_visible_area(product_image.convert("RGBA"))

    left, top, right, bottom = preset.safe_box
    max_width = right - left - BOX_PADDING * 2
    max_height = bottom - top - BOX_PADDING * 2

    fit_w, fit_h = fit_size(product.size, (max_width, max_height))
    scaled_w = max(1, round(fit_w * transform.scale))
    scaled_h = max(1, round(fit_h * transform.scale))
    resized = product.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)

    paste_x = left + (right - left - resized.width) // 2 + transform.offset_x
    paste_y = top + (bottom - top - resized.height) // 2 + transform.offset_y
    return resized, (paste_x, paste_y)


def _apply_layer_transform(
    layer: Image.Image,
    canvas_size: tuple[int, int],
    transform: LayerTransform,
) -> Image.Image:
    if transform.is_identity:
        return layer
    canvas_w, canvas_h = canvas_size
    new_w = max(1, round(canvas_w * transform.scale))
    new_h = max(1, round(canvas_h * transform.scale))
    resized = layer.resize((new_w, new_h), Image.Resampling.LANCZOS)
    stage = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    paste_x = (canvas_w - new_w) // 2 + transform.offset_x
    paste_y = (canvas_h - new_h) // 2 + transform.offset_y
    stage.paste(resized, (paste_x, paste_y), resized)
    return stage


def _open_product_image(product_path: Path) -> Image.Image:
    """Return a PIL image suitable for compositing. For videos, returns the
    first frame so preview / single-call code paths still work."""
    if is_video_file(product_path):
        from core.video import read_first_frame

        return read_first_frame(product_path)
    with Image.open(product_path) as image:
        return image.convert("RGBA")


def build_composite_frame(
    preset_id: str,
    product_image: Image.Image,
    background: Image.Image | None = None,
    foreground: Image.Image | None = None,
    *,
    background_transform: LayerTransform = IDENTITY_TRANSFORM,
    foreground_transform: LayerTransform = IDENTITY_TRANSFORM,
    product_transform: LayerTransform = IDENTITY_TRANSFORM,
) -> Image.Image:
    preset = get_layout_preset(preset_id)

    if background is None and foreground is None:
        raise ValueError("請至少選擇前景套框或後景底圖。")

    if background is not None and background.size != preset.canvas_size:
        raise ValueError("後景底圖尺寸未正規化到目前輸出比例。")
    if foreground is not None and foreground.size != preset.canvas_size:
        raise ValueError("前景套框尺寸未正規化到目前輸出比例。")

    if background is not None:
        bg_staged = _apply_layer_transform(background, preset.canvas_size, background_transform)
        canvas = bg_staged.copy() if bg_staged is background else bg_staged
    else:
        canvas = Image.new("RGBA", preset.canvas_size, (0, 0, 0, 0))

    product, paste_position = _place_product(preset, product_image, product_transform)

    overlay = Image.new("RGBA", preset.canvas_size, (0, 0, 0, 0))
    overlay.paste(product, paste_position, product)
    result = Image.alpha_composite(canvas, overlay)
    if foreground is not None:
        fg_staged = _apply_layer_transform(foreground, preset.canvas_size, foreground_transform)
        result = Image.alpha_composite(result, fg_staged)
    return flatten_on_white(result)


def build_composite(
    preset_id: str,
    product_path: Path,
    background: Image.Image | None = None,
    foreground: Image.Image | None = None,
    *,
    background_transform: LayerTransform = IDENTITY_TRANSFORM,
    foreground_transform: LayerTransform = IDENTITY_TRANSFORM,
    product_transform: LayerTransform = IDENTITY_TRANSFORM,
) -> Image.Image:
    product_image = _open_product_image(product_path)
    return build_composite_frame(
        preset_id,
        product_image,
        background=background,
        foreground=foreground,
        background_transform=background_transform,
        foreground_transform=foreground_transform,
        product_transform=product_transform,
    )


def build_layer_preview(
    preset_id: str,
    background: Image.Image | None = None,
    foreground: Image.Image | None = None,
    *,
    background_transform: LayerTransform = IDENTITY_TRANSFORM,
    foreground_transform: LayerTransform = IDENTITY_TRANSFORM,
) -> Image.Image:
    preset = get_layout_preset(preset_id)
    if background is None and foreground is None:
        raise ValueError("請至少選擇前景套框或後景底圖。")

    if background is not None:
        bg_staged = _apply_layer_transform(background, preset.canvas_size, background_transform)
        canvas = bg_staged.copy() if bg_staged is background else bg_staged
    else:
        canvas = Image.new("RGBA", preset.canvas_size, (0, 0, 0, 0))
    if foreground is not None:
        fg_staged = _apply_layer_transform(foreground, preset.canvas_size, foreground_transform)
        canvas = Image.alpha_composite(canvas, fg_staged)
    return flatten_on_white(canvas)


def list_products(input_dir: Path) -> list[Path]:
    return sorted(
        {
            path
            for path in input_dir.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        }
    )


def _process_video_product(
    product_path: Path,
    out_path: Path,
    preset_id: str,
    background: Image.Image | None,
    foreground: Image.Image | None,
    background_transform: LayerTransform,
    foreground_transform: LayerTransform,
    product_transform: LayerTransform,
    frame_progress: FrameProgressCallback | None,
    cancel_check: CancelCheckCallback | None,
) -> bool:
    """Composite each frame of product_path onto bg/fg and encode to out_path,
    preserving the original audio. Returns False if cancelled, True on success."""
    from core import video

    preset = get_layout_preset(preset_id)
    meta = video.probe_video(product_path)
    fps = meta.fps if meta.fps > 0 else 30.0
    total_frames = meta.frame_count

    temp_silent = out_path.with_name(f"{out_path.stem}.silent{out_path.suffix}")
    cancelled = False
    try:
        with video.open_writer(temp_silent, fps=fps, size=preset.canvas_size) as writer:
            for idx, frame in enumerate(video.iter_frames(product_path)):
                composite = build_composite_frame(
                    preset_id,
                    frame,
                    background=background,
                    foreground=foreground,
                    background_transform=background_transform,
                    foreground_transform=foreground_transform,
                    product_transform=product_transform,
                )
                writer.write(composite)
                if frame_progress is not None:
                    frame_progress(idx + 1, total_frames, product_path.name)
                if cancel_check is not None and cancel_check():
                    cancelled = True
                    break

        if cancelled:
            return False

        video.mux_audio(temp_silent, product_path, out_path)
        return True
    finally:
        if temp_silent.exists():
            try:
                temp_silent.unlink()
            except OSError:
                pass


def batch_composite(
    preset_id: str,
    input_dir: Path,
    output_dir: Path,
    background_path: Path | None = None,
    foreground_path: Path | None = None,
    background_crop_box: CropBox | None = None,
    foreground_crop_box: CropBox | None = None,
    *,
    background_transform: LayerTransform = IDENTITY_TRANSFORM,
    foreground_transform: LayerTransform = IDENTITY_TRANSFORM,
    product_transforms: dict[Path, LayerTransform] | None = None,
    frame_progress: FrameProgressCallback | None = None,
    cancel_check: CancelCheckCallback | None = None,
):
    """Generator that yields (current, total, output_path) after each product.

    `product_transforms` maps product Path → per-product `LayerTransform`.
    Products not in the dict use `IDENTITY_TRANSFORM`. Layer transforms apply
    uniformly to every product.

    For video products, per-frame progress can be observed via the optional
    `frame_progress` callback, and mid-video cancellation via `cancel_check`."""
    background, foreground = load_layers(
        preset_id,
        background_path,
        foreground_path,
        background_crop_box=background_crop_box,
        foreground_crop_box=foreground_crop_box,
    )
    products = list_products(input_dir)
    total = len(products)
    output_dir.mkdir(parents=True, exist_ok=True)
    product_transforms = product_transforms or {}

    for i, product_path in enumerate(products):
        product_transform = product_transforms.get(product_path, IDENTITY_TRANSFORM)
        if is_video_file(product_path):
            out = output_dir / f"{product_path.stem}{OUTPUT_SUFFIX}{product_path.suffix.lower()}"
            completed = _process_video_product(
                product_path,
                out,
                preset_id,
                background,
                foreground,
                background_transform,
                foreground_transform,
                product_transform,
                frame_progress,
                cancel_check,
            )
            if not completed:
                return
        else:
            out = output_dir / f"{product_path.stem}{OUTPUT_SUFFIX}.png"
            result = build_composite(
                preset_id,
                product_path,
                background=background,
                foreground=foreground,
                background_transform=background_transform,
                foreground_transform=foreground_transform,
                product_transform=product_transform,
            )
            result.save(out)
        yield i + 1, total, out
        if cancel_check is not None and cancel_check():
            return
