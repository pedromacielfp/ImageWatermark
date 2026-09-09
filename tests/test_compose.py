from pathlib import Path

from PIL import Image

from lib.compose import compose, encode_png
from lib.constants import CANVAS_SIZE
from lib.overlay import canvas_mask, corner_mask_path, overlay_path, render_overlay
from tests.conftest import BRAND_SVG


def _solid_photo(color: tuple[int, int, int, int] = (0, 255, 0, 255)) -> Image.Image:
    return Image.new("RGBA", CANVAS_SIZE, color=color)


def test_compose_output_is_canvas_size_rgba(fixture_svg: Path):
    result = compose(
        _solid_photo(),
        overlay=render_overlay(fixture_svg),
        mask=canvas_mask(fixture_svg),
    )
    assert result.size == CANVAS_SIZE
    assert result.mode == "RGBA"


def test_compose_corners_are_fully_transparent(fixture_svg: Path):
    result = compose(
        _solid_photo(),
        overlay=render_overlay(fixture_svg),
        mask=canvas_mask(fixture_svg),
    )
    for xy in (
        (0, 0),
        (CANVAS_SIZE[0] - 1, 0),
        (0, CANVAS_SIZE[1] - 1),
        (CANVAS_SIZE[0] - 1, CANVAS_SIZE[1] - 1),
    ):
        assert result.getpixel(xy)[3] == 0


def test_compose_keeps_photo_visible_in_center(fixture_svg: Path):
    photo = _solid_photo((0, 255, 0, 255))
    result = compose(
        photo,
        overlay=render_overlay(fixture_svg),
        mask=canvas_mask(fixture_svg),
    )
    cx, cy = CANVAS_SIZE[0] // 2, CANVAS_SIZE[1] // 2
    pixel = result.getpixel((cx, cy))
    assert pixel[3] == 255
    # Photo is green; overlay is 50% red. Green channel should remain visible.
    assert pixel[1] > 0


def test_compose_png_bytes_are_deterministic(fixture_svg: Path):
    photo = _solid_photo()
    overlay = render_overlay(fixture_svg)
    mask = canvas_mask(fixture_svg)
    first = encode_png(compose(photo, overlay=overlay, mask=mask))
    second = encode_png(compose(photo.copy(), overlay=overlay.copy(), mask=mask.copy()))
    assert first == second
    assert first[:8] == b"\x89PNG\r\n\x1a\n"


def test_compose_without_headline_keeps_photo():
    photo = _solid_photo((0, 255, 0, 255))
    result = compose(photo, overlay=render_overlay(), mask=canvas_mask(), headline=None)
    cx, cy = CANVAS_SIZE[0] // 2, CANVAS_SIZE[1] // 2
    assert result.getpixel((cx, cy))[1] > 0


def test_overlay_ai_only_compose_keeps_rounded_corners():
    result = compose(
        _solid_photo(),
        overlay=render_overlay(overlay_path("overlay_ai_only")),
        mask=canvas_mask(corner_mask_path()),
    )
    assert result.getpixel((0, 0))[3] == 0
    assert result.getpixel((CANVAS_SIZE[0] - 1, 0))[3] == 0


def test_brand_compose_corners_transparent_when_present():
    if not BRAND_SVG.exists():
        return
    result = compose(_solid_photo(), overlay=render_overlay(BRAND_SVG), mask=canvas_mask(BRAND_SVG))
    assert result.size == CANVAS_SIZE
    assert result.getpixel((0, 0))[3] == 0
