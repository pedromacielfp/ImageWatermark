from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

import streamlit.components.v1 as components

from lib.constants import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    DEFAULT_HEADLINE_FONT,
    HEADLINE_FONTS,
    TEXT_LINE_HEIGHT,
    TEXT_PADDING_X,
    TEXT_PADDING_Y,
    TEXT_SIZE_MAX,
    TEXT_SIZE_MIN,
    TEXT_SIZE_PX,
)
from lib.headline import clamp_size, clean_font, font_path

_COMPONENT_DIR = Path(__file__).resolve().parent.parent / "components" / "headline"
_headline_overlay = components.declare_component("headline_overlay", path=str(_COMPONENT_DIR))


@lru_cache(maxsize=1)
def _font_options() -> tuple[dict, ...]:
    options = []
    for name, (_, weight) in HEADLINE_FONTS.items():
        path = font_path(name)
        if not path.exists():
            continue
        font_b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        options.append({"name": name, "weight": weight, "data": f"data:font/ttf;base64,{font_b64}"})
    return tuple(options)


def _png_data_url(png: bytes | None) -> str:
    if not png:
        return ""
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def parse_editor_value(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    return {
        "text": str(value.get("text", "")),
        "x": int(value.get("x", TEXT_PADDING_X)),
        "y": int(value.get("y", 0)),
        "size": clamp_size(value.get("size", TEXT_SIZE_PX)),
        "font": clean_font(value.get("font")),
        "dragged": bool(value.get("dragged", False)),
        "status": str(value.get("status", "editing")),
        "rev": int(value.get("rev", 0)),
    }


def render_headline_editor(
    image_png: bytes,
    initial: dict,
    *,
    baked_png: bytes | None = None,
    baked_rev: int = -1,
    key: str | None = None,
) -> dict | None:
    """Client-side headline editor. Only reports back when the user clicks Done
    (status "done") or starts changing a finished headline (status "editing")."""
    value = _headline_overlay(
        image_data=_png_data_url(image_png),
        baked_data=_png_data_url(baked_png),
        baked_rev=baked_rev,
        fonts=list(_font_options()),
        font=initial.get("font", DEFAULT_HEADLINE_FONT),
        text=initial["text"],
        x=initial["x"],
        y=initial["y"],
        size=initial.get("size", TEXT_SIZE_PX),
        dragged=initial.get("dragged", False),
        rev=initial.get("rev", 0),
        canvas_width=CANVAS_WIDTH,
        canvas_height=CANVAS_HEIGHT,
        base_font_size=TEXT_SIZE_PX,
        base_line_height=TEXT_LINE_HEIGHT,
        min_size=TEXT_SIZE_MIN,
        max_size=TEXT_SIZE_MAX,
        padding_x=TEXT_PADDING_X,
        padding_y=TEXT_PADDING_Y,
        key=key,
        default=None,
    )
    return parse_editor_value(value)
