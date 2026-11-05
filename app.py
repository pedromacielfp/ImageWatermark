import streamlit as st

from lib.compose import compose, encode_png
from lib.constants import (
    ALL_OVERLAY_VARIANTS,
    BRANDS,
    CANVAS_SIZE,
    CROP_BOX_COLOR,
    DEFAULT_BRAND,
    DEFAULT_HEADLINE,
    DEFAULT_HEADLINE_FONT,
    DEFAULT_OVERLAY_BY_BRAND,
    DEFAULT_OVERLAY_VARIANT,
    OVERLAY_FILE_VARIANTS,
    OVERLAY_LABELS,
    OVERLAYS_BY_BRAND,
    PAGE_BACKGROUND,
    TEXT_SIZE_PX,
)
from lib.crop import crop_and_resize, load_image, render_cropper
from lib.headline import Headline, default_headline_position
from lib.headline_component import parse_editor_value, render_headline_editor
from lib.overlay import canvas_mask, corner_mask_path, overlay_for_variant, overlay_path

st.set_page_config(page_title="Image Watermark & Crop", layout="centered")
st.markdown(
    f"""
    <style>
      .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"],
      [data-testid="stToolbar"], [data-testid="stDecoration"] {{
        background: {PAGE_BACKGROUND};
      }}
      [data-testid="stHeader"] {{
        background: {PAGE_BACKGROUND};
      }}
      .stApp {{
        color: #ffffff;
      }}
      h1, h2, h3, h4, p, label, .stMarkdown, [data-testid="stCaption"] {{
        color: #ffffff !important;
      }}
      iframe {{
        background: {PAGE_BACKGROUND};
      }}
      [data-testid="stFileUploader"] section {{
        border-color: {CROP_BOX_COLOR};
      }}
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Image Watermark & Crop")
st.caption(
    "Upload a photo, crop it to 1400×840 (5:3), pick an overlay, optionally add headline text, and download a PNG."
)

missing_overlays = [name for name in OVERLAY_FILE_VARIANTS if not overlay_path(name).exists()]
if missing_overlays:
    st.error("Bundled overlay file(s) missing: " + ", ".join(f"`{name}.svg`" for name in missing_overlays))
    st.stop()


def _sync_overlay_checkboxes(variant: str) -> None:
    st.session_state.overlay_variant = variant
    for name in ALL_OVERLAY_VARIANTS:
        st.session_state[f"ov_{name}"] = name == variant


def _sync_brand_checkboxes(brand: str) -> None:
    brand_changed = st.session_state.get("brand") != brand
    st.session_state.brand = brand
    for name in BRANDS:
        st.session_state[f"brand_{name}"] = name == brand
    options = OVERLAYS_BY_BRAND[brand]
    current = st.session_state.get("overlay_variant")
    if brand_changed or current not in options:
        _sync_overlay_checkboxes(DEFAULT_OVERLAY_BY_BRAND[brand])


def _reconcile_brand_checkboxes() -> None:
    previous = st.session_state.get("brand", DEFAULT_BRAND)
    if all(f"brand_{name}" in st.session_state for name in BRANDS):
        checked = [name for name in BRANDS if st.session_state[f"brand_{name}"]]
        newly_checked = [name for name in checked if name != previous]
        if newly_checked:
            previous = newly_checked[-1]
    _sync_brand_checkboxes(previous)


def _reconcile_overlay_checkboxes() -> None:
    brand = st.session_state.get("brand", DEFAULT_BRAND)
    options = OVERLAYS_BY_BRAND[brand]
    previous = st.session_state.get("overlay_variant", DEFAULT_OVERLAY_BY_BRAND[brand])
    if previous not in options:
        previous = DEFAULT_OVERLAY_BY_BRAND[brand]
    if all(f"ov_{name}" in st.session_state for name in options):
        checked = [name for name in options if st.session_state[f"ov_{name}"]]
        newly_checked = [name for name in checked if name != previous]
        if newly_checked:
            previous = newly_checked[-1]
    _sync_overlay_checkboxes(previous)

uploaded = st.file_uploader(
    "Upload an image",
    type=["jpg", "jpeg", "png", "webp"],
)

if uploaded is None:
    st.session_state.pop("confirmed", None)
    st.stop()

file_id = f"{uploaded.name}-{uploaded.size}"
if st.session_state.get("file_id") != file_id:
    st.session_state.file_id = file_id
    st.session_state.confirmed = False
    st.session_state.headline = None
    st.session_state.headline_enabled = True
    st.session_state.brand = DEFAULT_BRAND
    st.session_state.overlay_variant = DEFAULT_OVERLAY_VARIANT
    for name in BRANDS:
        st.session_state[f"brand_{name}"] = name == DEFAULT_BRAND
    for name in ALL_OVERLAY_VARIANTS:
        st.session_state[f"ov_{name}"] = name == DEFAULT_OVERLAY_VARIANT

image = load_image(uploaded)

st.subheader("1. Crop")
st.write("Move and resize the box. The aspect ratio stays locked at 5:3.")
if "brand" not in st.session_state:
    st.session_state.brand = DEFAULT_BRAND
_reconcile_brand_checkboxes()
st.write("Brand")
brand_cols = st.columns(len(BRANDS))
for column, name in zip(brand_cols, BRANDS):
    with column:
        st.checkbox(name, key=f"brand_{name}")
box = render_cropper(image, key=f"cropper-{file_id}")

if st.button("Confirm crop", type="primary"):
    st.session_state.confirmed = True
    st.session_state.box = box

if not st.session_state.get("confirmed"):
    st.stop()

def _cached(slot: str, cache_key: tuple, build):
    entry = st.session_state.get(slot)
    if entry is None or entry[0] != cache_key:
        entry = (cache_key, build())
        st.session_state[slot] = entry
    return entry[1]


crop_key = (file_id, tuple(sorted(st.session_state.box.items())))
cropped = _cached("_cropped_cache", crop_key, lambda: crop_and_resize(image, st.session_state.box))

if "overlay_variant" not in st.session_state:
    st.session_state.overlay_variant = DEFAULT_OVERLAY_BY_BRAND[
        st.session_state.get("brand", DEFAULT_BRAND)
    ]
_reconcile_overlay_checkboxes()

brand = st.session_state.get("brand", DEFAULT_BRAND)
options = OVERLAYS_BY_BRAND[brand]

st.subheader("2. Overlay")
st.write("Check one overlay. The preview below updates as soon as you pick it.")
overlay_cols = st.columns(len(options))
for column, name in zip(overlay_cols, options):
    with column:
        st.checkbox(OVERLAY_LABELS[name], key=f"ov_{name}")

variant = st.session_state.get("overlay_variant", DEFAULT_OVERLAY_VARIANT)
overlay = overlay_for_variant(variant)
mask = canvas_mask(corner_mask_path())


def _build_base():
    composed = compose(cropped, overlay=overlay, mask=mask)
    return composed, encode_png(composed)


base_key = (*crop_key, variant)
base, base_png = _cached("_base_cache", base_key, _build_base)

if "headline_enabled" not in st.session_state:
    st.session_state.headline_enabled = True
if "headline_rev" not in st.session_state:
    st.session_state.headline_rev = 0

headline_header, headline_action = st.columns([3, 1])
with headline_header:
    st.subheader("3. Headline")
with headline_action:
    if st.session_state.headline_enabled:
        if st.button("Delete headline"):
            st.session_state.headline_enabled = False
            st.rerun()
    elif st.button("Add headline"):
        st.session_state.headline_enabled = True
        st.session_state.headline = None
        st.session_state.headline_rev += 1
        st.rerun()

final_png = None
if st.session_state.headline_enabled:
    editor_key = f"headline-{file_id}-{st.session_state.headline_rev}"
    latest = parse_editor_value(st.session_state.get(editor_key)) or st.session_state.get("headline")
    if latest is None:
        x, y = default_headline_position(DEFAULT_HEADLINE)
        latest = {
            "text": DEFAULT_HEADLINE,
            "x": x,
            "y": y,
            "size": TEXT_SIZE_PX,
            "font": DEFAULT_HEADLINE_FONT,
            "dragged": False,
            "status": "editing",
            "rev": 0,
        }
    st.session_state.headline = latest

    baked_png = None
    if latest["status"] == "done":
        headline = Headline(
            text=latest["text"],
            x=latest["x"],
            y=latest["y"],
            bottom_anchored=not latest["dragged"],
            size=latest["size"],
            font=latest.get("font", DEFAULT_HEADLINE_FONT),
        )
        baked_png = _cached(
            "_final_cache",
            (*base_key, headline),
            lambda: encode_png(compose(cropped, overlay=overlay, mask=mask, headline=headline)),
        )
    render_headline_editor(
        base_png,
        latest,
        baked_png=baked_png,
        baked_rev=latest["rev"] if baked_png else -1,
        key=editor_key,
    )
    final_png = baked_png
else:
    st.write("Headline removed. The download is crop + overlay only.")
    st.image(base, caption=f"Live preview · {variant}", output_format="PNG")
    final_png = base_png

st.subheader("4. Download")
if final_png is None:
    st.info("Finish the headline above and click **Done – prepare download** to get your PNG.")
else:
    st.download_button(
        f"Download PNG ({CANVAS_SIZE[0]}×{CANVAS_SIZE[1]})",
        data=final_png,
        file_name="watermarked.png",
        mime="image/png",
        type="primary",
    )
