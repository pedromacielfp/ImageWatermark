from PIL import Image

from lib.constants import (
    CANVAS_HEIGHT,
    CANVAS_SIZE,
    DEFAULT_HEADLINE,
    TEXT_LINE_HEIGHT,
    TEXT_PADDING_X,
    TEXT_PADDING_Y,
)
from lib.headline import (
    Headline,
    default_headline_position,
    draw_headline,
    wrap_text,
)


def test_default_copy_is_placeholder():
    assert DEFAULT_HEADLINE == "insert your text here"


def test_default_position_is_bottom_left_with_32px_padding():
    x, y = default_headline_position(DEFAULT_HEADLINE)
    assert x == TEXT_PADDING_X
    lines = wrap_text(DEFAULT_HEADLINE, max_width=CANVAS_SIZE[0] - 2 * TEXT_PADDING_X)
    block_h = len(lines) * TEXT_LINE_HEIGHT
    assert y == CANVAS_HEIGHT - TEXT_PADDING_Y - block_h


def test_wrap_text_breaks_long_words():
    huge = "A" * 200
    lines = wrap_text(huge, max_width=400)
    assert len(lines) > 1
    for line in lines:
        assert line


def test_draw_headline_bakes_white_pixels():
    image = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 255))
    x, y = default_headline_position("HELLO")
    result = draw_headline(image, Headline(text="HELLO", x=x, y=y))
    # A glyph should sit near the default bottom-left anchor.
    found_white = False
    for py in range(y, min(y + TEXT_LINE_HEIGHT, CANVAS_HEIGHT)):
        for px in range(x, min(x + 200, CANVAS_SIZE[0])):
            pixel = result.getpixel((px, py))
            if pixel[0] > 200 and pixel[1] > 200 and pixel[2] > 200 and pixel[3] == 255:
                found_white = True
                break
        if found_white:
            break
    assert found_white


def test_draw_headline_is_deterministic():
    image = Image.new("RGBA", CANVAS_SIZE, (10, 20, 30, 255))
    x, y = default_headline_position("insert your text here")
    headline = Headline(text="insert your text here", x=x, y=y)
    from lib.compose import encode_png

    first = encode_png(draw_headline(image.copy(), headline))
    second = encode_png(draw_headline(image.copy(), headline))
    assert first == second
