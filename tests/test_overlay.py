from pathlib import Path

import pytest
from PIL import Image

from lib.constants import CANVAS_SIZE
from lib.overlay import canvas_mask, overlay_for_variant, overlay_path, render_overlay
from tests.conftest import BRAND_SVG


def test_render_overlay_is_canvas_size_rgba(fixture_svg: Path):
    overlay = render_overlay(fixture_svg)
    assert overlay.size == CANVAS_SIZE
    assert overlay.mode == "RGBA"


def test_render_overlay_comes_from_svg_not_empty(fixture_svg: Path):
    overlay = render_overlay(fixture_svg)
    extrema = overlay.getextrema()
    alpha_max = extrema[3][1]
    assert alpha_max > 0


def test_canvas_mask_corners_are_transparent(fixture_svg: Path):
    mask = canvas_mask(fixture_svg)
    assert mask.size == CANVAS_SIZE
    assert mask.getpixel((0, 0)) == 0
    assert mask.getpixel((CANVAS_SIZE[0] - 1, 0)) == 0
    assert mask.getpixel((0, CANVAS_SIZE[1] - 1)) == 0
    assert mask.getpixel((CANVAS_SIZE[0] - 1, CANVAS_SIZE[1] - 1)) == 0


def test_canvas_mask_center_is_opaque(fixture_svg: Path):
    mask = canvas_mask(fixture_svg)
    cx, cy = CANVAS_SIZE[0] // 2, CANVAS_SIZE[1] // 2
    assert mask.getpixel((cx, cy)) == 255


def test_brand_overlay_renders_when_present():
    if not BRAND_SVG.exists():
        return
    overlay = render_overlay(BRAND_SVG)
    assert overlay.size == CANVAS_SIZE
    assert overlay.mode == "RGBA"
    assert overlay.getpixel((0, 0))[3] == 0


def test_overlay_ai_renders_swoosh_and_badge():
    path = overlay_path("overlay_ai")
    overlay = render_overlay(path)
    assert overlay.size == CANVAS_SIZE
    assert overlay.mode == "RGBA"
    assert overlay.getpixel((0, 0))[3] == 0
    swoosh = overlay.getpixel((200, 700))
    assert swoosh[0] > 80
    assert swoosh[3] > 200
    badge = overlay.getpixel((1352, 48))
    assert badge[3] > 50


def test_overlay_ai_only_is_badge_without_scrim():
    overlay = render_overlay(overlay_path("overlay_ai_only"))
    assert overlay.size == CANVAS_SIZE
    center = overlay.getpixel((CANVAS_SIZE[0] // 2, CANVAS_SIZE[1] // 2))
    assert center[3] == 0
    badge = overlay.getpixel((1352, 48))
    assert badge[3] > 50


def test_overlay_path_rejects_unknown_variant():
    with pytest.raises(ValueError, match="Unknown overlay variant"):
        overlay_path("not_a_real_overlay")
    with pytest.raises(ValueError, match="Unknown overlay variant"):
        overlay_path("none")


def test_none_overlay_is_fully_transparent():
    overlay = overlay_for_variant("none")
    assert overlay.size == CANVAS_SIZE
    assert overlay.mode == "RGBA"
    assert overlay.getpixel((700, 420))[3] == 0
    assert overlay.getpixel((1352, 48))[3] == 0


def test_brand_overlay_keeps_scrim_and_swoosh():
    """The SVG has a full-canvas dark gradient plus magenta swooshes — both must render."""
    if not BRAND_SVG.exists():
        return
    overlay = render_overlay(BRAND_SVG)
    scrim = overlay.getpixel((1200, 780))
    assert scrim[3] > 100
    assert scrim[0] < 40 and scrim[1] < 40
    swoosh = overlay.getpixel((200, 700))
    assert swoosh[0] > 80
    assert swoosh[3] > 200
