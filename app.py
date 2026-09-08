import streamlit as st

from lib.compose import compose, encode_png
from lib.constants import CANVAS_SIZE, CROP_BOX_COLOR, DEFAULT_HEADLINE, PAGE_BACKGROUND
from lib.crop import crop_and_resize, load_image, render_cropper
from lib.headline import Headline, default_headline_position
from lib.headline_component import render_headline_editor
from lib.overlay import canvas_mask, default_overlay_path, render_overlay

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
    "Upload a photo, crop it to 1400×840 (5:3), add headline text, and download a PNG with the brand overlay."
)

overlay_path = default_overlay_path()
if not overlay_path.exists():
    st.error(f"Bundled overlay is missing: `{overlay_path}`")
    st.stop()

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
overlay = render_overlay(overlay_path)
mask = canvas_mask(overlay_path)
base = compose(cropped, overlay=overlay, mask=mask)

if st.session_state.headline is None:
    x, y = default_headline_position(DEFAULT_HEADLINE)
    st.session_state.headline = {
        "text": DEFAULT_HEADLINE,
        "x": x,
        "y": y,
        "dragged": False,
    }

st.subheader("2. Headline")
st.write("Drag to reposition. Click the text to edit it. The download includes crop, overlay, and text.")
edited = render_headline_editor(
    encode_png(base),
    text=st.session_state.headline["text"],
    x=st.session_state.headline["x"],
    y=st.session_state.headline["y"],
    key=f"headline-{file_id}",
)
st.session_state.headline = edited

headline = Headline(
    text=edited["text"],
    x=edited["x"],
    y=edited["y"],
    bottom_anchored=not edited["dragged"],
)
final = compose(cropped, overlay=overlay, mask=mask, headline=headline)

st.subheader("3. Download")
st.image(final, caption=f"{CANVAS_SIZE[0]}×{CANVAS_SIZE[1]} PNG", output_format="PNG")
st.download_button(
    "Download PNG",
    data=encode_png(final),
    file_name="watermarked.png",
    mime="image/png",
    type="primary",
)
