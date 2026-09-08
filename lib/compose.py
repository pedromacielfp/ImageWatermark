from __future__ import annotations

import io

from PIL import Image, ImageChops

from lib.constants import CANVAS_SIZE, PNG_COMPRESS_LEVEL
from lib.headline import Headline, draw_headline
from lib.overlay import canvas_mask, render_overlay


def compose(
    photo: Image.Image,
    overlay: Image.Image | None = None,
    mask: Image.Image | None = None,
    headline: Headline | None = None,
) -> Image.Image:
    """Composite overlay (and optional headline) on the photo, then clip corners."""
    photo = photo.convert("RGBA")
    if photo.size != CANVAS_SIZE:
        raise ValueError(f"Photo must be {CANVAS_SIZE}, got {photo.size}")

    if overlay is None:
        overlay = render_overlay()
    overlay = overlay.convert("RGBA")
    if overlay.size != CANVAS_SIZE:
        overlay = overlay.resize(CANVAS_SIZE, Image.Resampling.LANCZOS)

    composed = Image.alpha_composite(photo, overlay)
    if headline is not None:
        composed = draw_headline(composed, headline)

    if mask is None:
        mask = canvas_mask()
    mask_l = mask.convert("L")
    if mask_l.size != CANVAS_SIZE:
        mask_l = mask_l.resize(CANVAS_SIZE, Image.Resampling.LANCZOS)

    red, green, blue, alpha = composed.split()
    clipped_alpha = ImageChops.multiply(alpha, mask_l)
    return Image.merge("RGBA", (red, green, blue, clipped_alpha))


def encode_png(image: Image.Image) -> bytes:
    """Deterministic PNG bytes (no timestamps)."""
    buffer = io.BytesIO()
    image.save(
        buffer,
        format="PNG",
        compress_level=PNG_COMPRESS_LEVEL,
        optimize=False,
    )
    return buffer.getvalue()
