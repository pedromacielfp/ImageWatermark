from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from lib.constants import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    TEXT_COLOR,
    TEXT_LINE_HEIGHT,
    TEXT_PADDING_X,
    TEXT_PADDING_Y,
    TEXT_SIZE_PX,
)


@dataclass(frozen=True)
class Headline:
    text: str
    x: int
    y: int
    bottom_anchored: bool = False


def default_font_path() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "fonts" / "EurowingsWeb-Black.ttf"


@lru_cache(maxsize=1)
def load_font() -> ImageFont.FreeTypeFont:
    path = default_font_path()
    if not path.exists():
        raise FileNotFoundError(
            f"Headline font missing: {path}. Place EurowingsWeb-Black.ttf in assets/fonts/."
        )
    return ImageFont.truetype(str(path), TEXT_SIZE_PX)


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
) -> tuple[int, int]:
    font = font or load_font()
    if max_width is None:
        max_width = CANVAS_WIDTH - 2 * TEXT_PADDING_X
    lines = wrap_text(text, max_width=max_width, font=font)
    block_h = max(1, len(lines)) * TEXT_LINE_HEIGHT
    x = TEXT_PADDING_X
    y = CANVAS_HEIGHT - TEXT_PADDING_Y - block_h
    return x, y


def resolve_headline(headline: Headline) -> Headline:
    font = load_font()
    max_width = CANVAS_WIDTH - headline.x - TEXT_PADDING_X
    if headline.bottom_anchored:
        x, y = default_headline_position(headline.text, font=font)
        return Headline(text=headline.text, x=x, y=y, bottom_anchored=True)
    return Headline(
        text=headline.text,
        x=headline.x,
        y=headline.y,
        bottom_anchored=False,
    )


def draw_headline(image: Image.Image, headline: Headline) -> Image.Image:
    """Paint headline text into a copy of the image at canvas coordinates."""
    font = load_font()
    placed = resolve_headline(headline)
    max_width = max(1, CANVAS_WIDTH - placed.x - TEXT_PADDING_X)
    lines = wrap_text(placed.text, max_width=max_width, font=font)
    out = image.convert("RGBA").copy()
    draw = ImageDraw.Draw(out)
    for index, line in enumerate(lines):
        top = placed.y + index * TEXT_LINE_HEIGHT
        draw.text((placed.x, top), line, font=font, fill=TEXT_COLOR, anchor="lt")
    return out
