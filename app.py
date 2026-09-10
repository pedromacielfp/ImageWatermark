import streamlit as st

from lib.compose import compose, encode_png
from lib.constants import (
    CANVAS_SIZE,
    CROP_BOX_COLOR,
    DEFAULT_HEADLINE,
    DEFAULT_OVERLAY_VARIANT,
    OVERLAY_FILE_VARIANTS,
    OVERLAY_LABELS,
    OVERLAY_VARIANTS,
    PAGE_BACKGROUND,
)
from lib.crop import crop_and_resize, load_image, render_cropper
from lib.headline import Headline, default_headline_position
from lib.headline_component import render_headline_editor
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
    for name in OVERLAY_VARIANTS:
        st.session_state[f"ov_{name}"] = name == variant


def _reconcile_overlay_checkboxes() -> None:
    """Keep exactly one overlay checked. Must run before the checkbox widgets render."""
    previous = st.session_state.get("overlay_variant", DEFAULT_OVERLAY_VARIANT)
    if all(f"ov_{name}" in st.session_state for name in OVERLAY_VARIANTS):
        checked = [name for name in OVERLAY_VARIANTS if st.session_state[f"ov_{name}"]]
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

image = load_image(uploaded)

st.subheader("1. Crop")
st.write("Move and resize the box. The aspect ratio stays locked at 5:3.")
box = render_cropper(image, key=f"cropper-{file_id}")

if st.button("Confirm crop", type="primary"):
    st.session_state.confirmed = True
    st.session_state.box = box
    st.session_state.headline = None

if not st.session_state.get("confirmed"):
    st.stop()

cropped = crop_and_resize(image, st.session_state.box)

if "overlay_variant" not in st.session_state:
    st.session_state.overlay_variant = DEFAULT_OVERLAY_VARIANT
_reconcile_overlay_checkboxes()

st.subheader("2. Overlay")
st.write("Check one overlay. The preview below updates as soon as you pick it.")
overlay_cols = st.columns(len(OVERLAY_VARIANTS))
for column, name in zip(overlay_cols, OVERLAY_VARIANTS):
    with column:
        st.checkbox(OVERLAY_LABELS[name], key=f"ov_{name}")

variant = st.session_state.get("overlay_variant", DEFAULT_OVERLAY_VARIANT)
overlay = overlay_for_variant(variant)
mask = canvas_mask(corner_mask_path())
base = compose(cropped, overlay=overlay, mask=mask)

if "headline_enabled" not in st.session_state:
    st.session_state.headline_enabled = True

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
        st.rerun()

if st.session_state.headline_enabled:
    st.write("Drag to reposition. Click the text to edit it.")
    if st.session_state.headline is None:
        x, y = default_headline_position(DEFAULT_HEADLINE)
        st.session_state.headline = {
            "text": DEFAULT_HEADLINE,
            "x": x,
            "y": y,
            "dragged": False,
        }
    headline = Headline(
        text=st.session_state.headline["text"],
        x=st.session_state.headline["x"],
        y=st.session_state.headline["y"],
        bottom_anchored=not st.session_state.headline.get("dragged", False),
    )
    baked = compose(cropped, overlay=overlay, mask=mask, headline=headline)
    edited = render_headline_editor(
        encode_png(base),
        text=st.session_state.headline["text"],
        x=st.session_state.headline["x"],
        y=st.session_state.headline["y"],
        baked_png=encode_png(baked),
        overlay_variant=variant,
        dragged=st.session_state.headline.get("dragged", False),
        key=f"headline-{file_id}-{variant}",
    )
    st.session_state.headline = edited
    headline = Headline(
        text=edited["text"],
        x=edited["x"],
        y=edited["y"],
        bottom_anchored=not edited["dragged"],
    )
    final = compose(cropped, overlay=overlay, mask=mask, headline=headline)
else:
    st.write("Headline removed. The download is crop + overlay only.")
    st.image(base, caption=f"Live preview · {variant}", output_format="PNG")
    final = base

st.subheader("4. Download")
st.image(final, caption=f"{CANVAS_SIZE[0]}×{CANVAS_SIZE[1]} PNG", output_format="PNG")
st.download_button(
    "Download PNG",
    data=encode_png(final),
    file_name="watermarked.png",
    mime="image/png",
    type="primary",
)
