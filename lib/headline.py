from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from lib.constants import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    DEFAULT_HEADLINE_FONT,
    HEADLINE_FONTS,
    TEXT_COLOR,
    TEXT_LINE_HEIGHT,
    TEXT_PADDING_X,
    TEXT_PADDING_Y,
    TEXT_SIZE_MAX,
    TEXT_SIZE_MIN,
    TEXT_SIZE_PX,
)


@dataclass(frozen=True)
class Headline:
    text: str
    x: int
    y: int
    bottom_anchored: bool = False
    size: int = TEXT_SIZE_PX
    font: str = DEFAULT_HEADLINE_FONT


def clean_font(font: object) -> str:
    return font if font in HEADLINE_FONTS else DEFAULT_HEADLINE_FONT


def clamp_size(size: int) -> int:
    return max(TEXT_SIZE_MIN, min(TEXT_SIZE_MAX, int(size)))


def line_height_for(size: int) -> int:
    """Keep the 95px / 112px ratio at every size (must match the editor's JS)."""
    return round(clamp_size(size) * TEXT_LINE_HEIGHT / TEXT_SIZE_PX)


def font_path(font: str = DEFAULT_HEADLINE_FONT) -> Path:
    filename = HEADLINE_FONTS[clean_font(font)][0]
    return Path(__file__).resolve().parent.parent / "assets" / "fonts" / filename


def default_font_path() -> Path:
    return font_path(DEFAULT_HEADLINE_FONT)


@lru_cache(maxsize=32)
def load_font(size: int = TEXT_SIZE_PX, font: str = DEFAULT_HEADLINE_FONT) -> ImageFont.FreeTypeFont:
    path = font_path(font)
    if not path.exists():
        raise FileNotFoundError(f"Headline font missing: {path}. Place {path.name} in assets/fonts/.")
    return ImageFont.truetype(str(path), clamp_size(size))


def _text_width(text: str, font: ImageFont.FreeTypeFont) -> int:
    if not text:
        return 0
    return int(font.getlength(text))


def wrap_text(
    text: str,
    max_width: int | None = None,
    font: ImageFont.FreeTypeFont | None = None,
) -> list[str]:
    """CSS overflow-wrap: break-word — wrap on spaces, then mid-word if needed."""
    font = font or load_font()
    if max_width is None:
        max_width = CANVAS_WIDTH - 2 * TEXT_PADDING_X
    max_width = max(1, max_width)

    lines: list[str] = []
    for paragraph in text.replace("\r\n", "\n").split("\n"):
        if paragraph == "":
            lines.append("")
            continue
        current = ""
        for word in paragraph.split(" "):
            candidate = word if current == "" else f"{current} {word}"
            if _text_width(candidate, font) <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
            if _text_width(word, font) <= max_width:
                current = word
                continue
            chunk = ""
            for char in word:
                trial = chunk + char
                if _text_width(trial, font) <= max_width or chunk == "":
                    chunk = trial
                else:
                    lines.append(chunk)
                    chunk = char
            current = chunk
        lines.append(current)
    return lines or [""]


def default_headline_position(
    text: str,
    max_width: int | None = None,
    font: ImageFont.FreeTypeFont | None = None,
    size: int = TEXT_SIZE_PX,
) -> tuple[int, int]:
    font = font or load_font(size)
    size = clamp_size(size)
    if max_width is None:
        max_width = CANVAS_WIDTH - 2 * TEXT_PADDING_X
    lines = wrap_text(text, max_width=max_width, font=font)
    block_h = max(1, len(lines)) * line_height_for(size)
    x = TEXT_PADDING_X
    y = CANVAS_HEIGHT - TEXT_PADDING_Y - block_h
    return x, y


def resolve_headline(headline: Headline) -> Headline:
    size = clamp_size(headline.size)
    font_name = clean_font(headline.font)
    x, y = headline.x, headline.y
    if headline.bottom_anchored:
        x, y = default_headline_position(headline.text, font=load_font(size, font_name), size=size)
    return Headline(
        text=headline.text,
        x=x,
        y=y,
        bottom_anchored=headline.bottom_anchored,
        size=size,
        font=font_name,
    )


def draw_headline(image: Image.Image, headline: Headline) -> Image.Image:
    """Paint headline text into a copy of the image at canvas coordinates."""
    placed = resolve_headline(headline)
    font = load_font(placed.size, placed.font)
    line_height = line_height_for(placed.size)
    max_width = max(1, CANVAS_WIDTH - placed.x - TEXT_PADDING_X)
    lines = wrap_text(placed.text, max_width=max_width, font=font)
    out = image.convert("RGBA").copy()
    draw = ImageDraw.Draw(out)
    for index, line in enumerate(lines):
        top = placed.y + index * line_height
        draw.text((placed.x, top), line, font=font, fill=TEXT_COLOR, anchor="lt")
    return out
