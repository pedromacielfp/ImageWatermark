from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, Mapping

from PIL import Image, ImageOps

from lib.constants import ASPECT_RATIO, CANVAS_SIZE, CROP_BOX_COLOR

Box = Mapping[str, int]


def load_image(source: str | Path | BinaryIO) -> Image.Image:
    """Open an uploaded image and apply EXIF orientation."""
    image = Image.open(source)
    image = ImageOps.exif_transpose(image) or image
    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGBA") if "A" in image.getbands() else image.convert("RGB")
    return image


def snap_box_to_aspect(
    box: Box,
    image_size: tuple[int, int],
    ratio: tuple[int, int] = ASPECT_RATIO,
) -> dict[str, int]:
    """Force a crop box to `ratio` and keep it inside the image."""
    left = int(box["left"])
    top = int(box["top"])
    width = max(1, int(box["width"]))
    height = max(1, int(box["height"]))
    img_w, img_h = image_size
    rw, rh = ratio
    target = rw / rh

    if width / height > target:
        new_width = max(rw, round(height * target))
        left += (width - new_width) // 2
        width = new_width
    else:
        new_height = max(rh, round(width / target))
        top += (height - new_height) // 2
        height = new_height

    if width > img_w:
        width = img_w
        height = max(rh, round(width / target))
    if height > img_h:
        height = img_h
        width = max(rw, round(height * target))
        if width > img_w:
            width = img_w
            height = max(1, round(width / target))

    width = min(width, img_w)
    height = min(height, img_h)
    left = max(0, min(left, img_w - width))
    top = max(0, min(top, img_h - height))
    return {"left": int(left), "top": int(top), "width": int(width), "height": int(height)}


def crop_and_resize(image: Image.Image, box: Box) -> Image.Image:
    """Crop original pixels to a 5:3 box, then Lanczos-resize to the canvas."""
    snapped = snap_box_to_aspect(box, image.size)
    left = snapped["left"]
    top = snapped["top"]
    cropped = image.crop((left, top, left + snapped["width"], top + snapped["height"]))
    return cropped.resize(CANVAS_SIZE, Image.Resampling.LANCZOS)


def render_cropper(image: Image.Image, key: str | None = None) -> dict[str, int]:
    """Interactive 5:3 crop box; returns coordinates on the original image."""
    from streamlit_cropper import st_cropper

    rect = st_cropper(
        image,
        realtime_update=True,
        aspect_ratio=ASPECT_RATIO,
        return_type="box",
        box_color=CROP_BOX_COLOR,
        stroke_width=3,
        key=key,
        should_resize_image=True,
    )
    return {
        "left": int(rect["left"]),
        "top": int(rect["top"]),
        "width": int(rect["width"]),
        "height": int(rect["height"]),
    }
