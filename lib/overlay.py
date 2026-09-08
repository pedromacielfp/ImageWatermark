from __future__ import annotations

import functools
import io
import xml.etree.ElementTree as ET
from pathlib import Path

import resvg_py
from PIL import Image

from lib.constants import (
    CANVAS_HEIGHT,
    CANVAS_SIZE,
    CANVAS_WIDTH,
    OVERLAY_RENDER_SCALE,
)

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def default_overlay_path() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "overlay.svg"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def normalize_svg(svg_text: str) -> str:
    """Make implicit gradient stops explicit so the renderer keeps every painted layer."""
    root = ET.fromstring(svg_text)
    for element in root.iter():
        if _local_name(element.tag) != "stop":
            continue
        style = element.get("style") or ""
        if element.get("stop-color") is None and "stop-color" not in style:
            element.set("stop-color", "#000000")
        if element.get("offset") is None:
            element.set("offset", "0")
    return ET.tostring(root, encoding="unicode")


def clip_mask_svg(svg_text: str) -> bytes:
    """Keep the SVG clip-path and fill the viewBox with opaque white."""
    root = ET.fromstring(svg_text)
    ns_prefix = ""
    if root.tag.startswith("{"):
        ns_prefix = root.tag.split("}")[0] + "}"

    clip_ref = None
    for element in root.iter():
        ref = element.get("clip-path")
        if ref:
            clip_ref = ref
            break

    view_box = root.get("viewBox")
    if view_box:
        parts = view_box.replace(",", " ").split()
        x, y, width, height = parts[0], parts[1], parts[2], parts[3]
    else:
        x, y = "0", "0"
        width = "".join(ch for ch in root.get("width", str(CANVAS_WIDTH)) if ch.isdigit() or ch == ".")
        height = "".join(ch for ch in root.get("height", str(CANVAS_HEIGHT)) if ch.isdigit() or ch == ".")

    for child in list(root):
        if _local_name(child.tag) != "defs":
            root.remove(child)

    group = ET.Element(f"{ns_prefix}g")
    if clip_ref:
        group.set("clip-path", clip_ref)
    rect = ET.SubElement(group, f"{ns_prefix}rect")
    rect.set("x", x)
    rect.set("y", y)
    rect.set("width", width)
    rect.set("height", height)
    rect.set("fill", "#FFFFFF")
    rect.set("fill-opacity", "1")
    root.append(group)
    xml = ET.tostring(root, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml}'.encode("utf-8")


def _svg_to_png_bytes(svg_bytes: bytes, width: int, height: int) -> bytes:
    return resvg_py.svg_to_bytes(
        svg_string=svg_bytes.decode("utf-8"),
        width=width,
        height=height,
    )


@functools.lru_cache(maxsize=8)
def _render_png_bytes(svg_path: str, width: int, height: int, mask: bool) -> bytes:
    svg_text = Path(svg_path).read_text(encoding="utf-8")
    payload = clip_mask_svg(svg_text) if mask else (
        '<?xml version="1.0" encoding="UTF-8"?>\n' + normalize_svg(svg_text)
    ).encode("utf-8")
    return _svg_to_png_bytes(payload, width, height)


def _render_at(svg_path: str | Path | None, size: tuple[int, int], mask: bool) -> Image.Image:
    path = str((Path(svg_path) if svg_path is not None else default_overlay_path()).resolve())
    hi_w = size[0] * OVERLAY_RENDER_SCALE
    hi_h = size[1] * OVERLAY_RENDER_SCALE
    png_bytes = _render_png_bytes(path, hi_w, hi_h, mask)
    image = Image.open(io.BytesIO(png_bytes))
    image = image.convert("L" if mask else "RGBA")
    if image.size != size:
        image = image.resize(size, Image.Resampling.LANCZOS)
    return image


def render_overlay(svg_path: str | Path | None = None, size: tuple[int, int] = CANVAS_SIZE) -> Image.Image:
    """Render the bundled SVG at 2x, then downscale to `size`."""
    return _render_at(svg_path, size, mask=False)


def canvas_mask(svg_path: str | Path | None = None, size: tuple[int, int] = CANVAS_SIZE) -> Image.Image:
    """Opaque inside the SVG clip-path, transparent outside (L mode)."""
    return _render_at(svg_path, size, mask=True)
