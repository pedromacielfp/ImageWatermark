from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_SVG = Path(__file__).resolve().parent / "fixtures" / "rounded_overlay.svg"
BRAND_SVG = ROOT / "assets" / "overlay.svg"


@pytest.fixture
def fixture_svg() -> Path:
    return FIXTURE_SVG
