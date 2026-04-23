"""Video decode / encode / audio-mux helpers for xFRAME808.

MVP scope: product inputs may be opaque videos (.mp4/.mov/.m4v/.webm).
Background and foreground stay static images. Output container matches
input; original audio track is preserved via ffmpeg mux.
"""
from __future__ import annotations

import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from PIL import Image

VIDEO_EXTENSIONS = (".mp4", ".mov", ".m4v", ".webm")


def is_video_file(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


@dataclass(frozen=True)
class VideoMetadata:
    fps: float
    frame_count: int
    size: tuple[int, int]


def _ffmpeg_exe() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def probe_video(path: Path) -> VideoMetadata:
    import imageio_ffmpeg

    reader = imageio_ffmpeg.read_frames(str(path))
    try:
        meta = next(reader)
    finally:
        reader.close()

    fps = float(meta.get("fps") or 30.0)
    duration = float(meta.get("duration") or 0.0)
    raw_size = meta.get("size") or (0, 0)
    size = (int(raw_size[0]), int(raw_size[1]))
    frame_count = max(1, int(round(duration * fps))) if duration > 0 else 1
    return VideoMetadata(fps=fps, frame_count=frame_count, size=size)


def iter_frames(path: Path) -> Iterator[Image.Image]:
    """Yield each video frame as a PIL RGB image (opaque)."""
    import imageio_ffmpeg

    reader = imageio_ffmpeg.read_frames(str(path))
    try:
        meta = next(reader)
        raw_size = meta["size"]
        width, height = int(raw_size[0]), int(raw_size[1])
        for raw in reader:
            yield Image.frombytes("RGB", (width, height), raw)
    finally:
        reader.close()


def read_first_frame(path: Path) -> Image.Image:
    for frame in iter_frames(path):
        return frame.convert("RGBA")
    raise ValueError(f"影片讀取失敗或無畫面：{path.name}")


def _codec_for(out_path: Path) -> tuple[str, str]:
    ext = out_path.suffix.lower()
    if ext == ".webm":
        return "libvpx-vp9", "yuv420p"
    return "libx264", "yuv420p"


class _VideoWriter:
    def __init__(self, out_path: Path, fps: float, size: tuple[int, int]):
        import imageio_ffmpeg

        codec, pix_fmt = _codec_for(out_path)
        self._writer = imageio_ffmpeg.write_frames(
            str(out_path),
            size,
            fps=fps,
            codec=codec,
            pix_fmt_in="rgb24",
            pix_fmt_out=pix_fmt,
            macro_block_size=1,
        )
        self._writer.send(None)
        self._size = size

    def write(self, frame: Image.Image) -> None:
        rgb = frame if frame.mode == "RGB" else frame.convert("RGB")
        if rgb.size != self._size:
            rgb = rgb.resize(self._size, Image.Resampling.LANCZOS)
        self._writer.send(rgb.tobytes())

    def close(self) -> None:
        self._writer.close()


@contextmanager
def open_writer(out_path: Path, fps: float, size: tuple[int, int]):
    writer = _VideoWriter(out_path, fps, size)
    try:
        yield writer
    finally:
        writer.close()


def mux_audio(silent_video: Path, audio_source: Path, out_path: Path) -> None:
    """Copy silent_video's video stream and audio_source's audio into out_path.

    If audio_source has no audio stream, the output is silent (no error).
    If `copy` of the audio codec fails for the target container, re-encode
    to the container default.
    """
    ffmpeg = _ffmpeg_exe()
    base_cmd = [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(silent_video),
        "-i",
        str(audio_source),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0?",
        "-c:v",
        "copy",
        "-shortest",
    ]

    try:
        subprocess.run(
            base_cmd + ["-c:a", "copy", str(out_path)],
            check=True,
            capture_output=True,
        )
        return
    except subprocess.CalledProcessError:
        pass

    fallback_codec = "libopus" if out_path.suffix.lower() == ".webm" else "aac"
    subprocess.run(
        base_cmd + ["-c:a", fallback_codec, str(out_path)],
        check=True,
        capture_output=True,
    )
