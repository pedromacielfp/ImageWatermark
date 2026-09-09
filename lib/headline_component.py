from __future__ import annotations

import base64
from pathlib import Path

import streamlit.components.v1 as components

from lib.constants import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    TEXT_FONT_WEIGHT,
    TEXT_LINE_HEIGHT,
    TEXT_PADDING_X,
    TEXT_PADDING_Y,
    TEXT_SIZE_PX,
)
from lib.headline import default_font_path

_COMPONENT_DIR = Path(__file__).resolve().parent.parent / "components" / "headline"
_headline_overlay = components.declare_component("headline_overlay", path=str(_COMPONENT_DIR))


def render_headline_editor(
    image_png: bytes,
    text: str,
    x: int,
    y: int,
    *,
    overlay_variant: str = "overlay",
    dragged: bool = False,
    key: str | None = None,
) -> dict:
    """Live headline: drag to move, click to edit. Coordinates are canvas pixels."""
    font_b64 = base64.b64encode(default_font_path().read_bytes()).decode("ascii")
    image_b64 = base64.b64encode(image_png).decode("ascii")
    value = _headline_overlay(
        image_data=f"data:image/png;base64,{image_b64}",
        font_data=f"data:font/ttf;base64,{font_b64}",
        text=text,
        x=x,
        y=y,
        canvas_width=CANVAS_WIDTH,
        canvas_height=CANVAS_HEIGHT,
        font_size=TEXT_SIZE_PX,
        line_height=TEXT_LINE_HEIGHT,
        font_weight=TEXT_FONT_WEIGHT,
        padding_x=TEXT_PADDING_X,
        padding_y=TEXT_PADDING_Y,
        overlay_variant=overlay_variant,
        key=key,
        default={"text": text, "x": x, "y": y, "dragged": dragged},
    )
    if not value:
        return {"text": text, "x": x, "y": y, "dragged": dragged}
    return {
        "text": str(value.get("text", text)),
        "x": int(value.get("x", x)),
        "y": int(value.get("y", y)),
        "dragged": bool(value.get("dragged", False)),
    }
