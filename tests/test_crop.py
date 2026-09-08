from pathlib import Path

from PIL import Image

from lib.constants import CANVAS_SIZE
from lib.crop import crop_and_resize, load_image, snap_box_to_aspect


def test_snap_box_locks_five_by_three_aspect():
    box = snap_box_to_aspect(
        {"left": 0, "top": 0, "width": 1000, "height": 1000},
        image_size=(2000, 2000),
    )
    assert abs((box["width"] / box["height"]) - (5 / 3)) < 0.01


def test_crop_and_resize_emits_exact_canvas_size():
    image = Image.new("RGB", (2000, 1500), color=(10, 20, 30))
    box = {"left": 100, "top": 50, "width": 1500, "height": 900}
    result = crop_and_resize(image, box)
    assert result.size == CANVAS_SIZE


def test_crop_does_not_distort_aspect_before_resize():
    image = Image.new("RGB", (2000, 1200), color=(255, 0, 0))
    box = snap_box_to_aspect(
        {"left": 0, "top": 0, "width": 2000, "height": 1200},
        image_size=image.size,
    )
    assert abs((box["width"] / box["height"]) - (5 / 3)) < 0.01
    result = crop_and_resize(image, box)
    assert result.size == CANVAS_SIZE


def test_load_image_converts_to_rgb_compatible(tmp_path: Path):
    source = Image.new("RGB", (80, 40), color=(1, 2, 3))
    path = tmp_path / "in.jpg"
    source.save(path, format="JPEG")
    loaded = load_image(path)
    assert loaded.mode in {"RGB", "RGBA"}
    assert loaded.size == (80, 40)
