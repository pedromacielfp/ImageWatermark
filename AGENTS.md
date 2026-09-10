# AGENTS.md

## Project: Image Watermark & Crop Tool

A small internal Streamlit web app that lets a user upload any image, interactively
choose how it's cropped to a fixed 1400x840px canvas, stamp a fixed brand overlay
(SVG) on top — preserving the overlay's exact size, gradients, opacity, and rounded
corners — then overlay editable headline text. No generative AI is used anywhere in
this pipeline; every operation must be deterministic image processing (cropping,
resizing, compositing, text rasterization), so the same input always produces the
same output.

---

## Core requirements

### 1. Bundled overlay asset
- The overlay SVG (`assets/overlay.svg`) ships with the app itself — it is a fixed
  design asset, not something the user uploads or the app modifies.
- It must be rendered from the SVG source (not a rasterized PNG guess) using a
  proper SVG renderer so **all** painted layers in the SVG
  (bottom scrim/shadow gradient, magenta swooshes, transparency, and the
  rounded-corner clip-path) are reproduced exactly. Do not drop implicit gradient
  stops (missing `stop-color` means black per the SVG spec).
- Render it once at app startup (or cache the render) at high resolution
  (e.g. 2x the target canvas: 2800x1680) so it stays crisp regardless of final
  output size, then downscale to match the canvas as needed.

### 2. Image upload
- Accept any common image format (JPEG, PNG, WEBP) via a file uploader.
- No size or aspect-ratio restriction on the input — the crop step handles that.

### 3. Interactive crop selection
- After upload, show the user an interactive cropping UI where they can move/resize
  a crop box over their image.
- The crop box must be **locked to a 1400:840 aspect ratio** (5:3) at all times —
  the user can reposition and scale it, but never distort it into a different ratio.
- Recommended library: `streamlit-cropper` (or equivalent) for the interactive
  drag/resize UI within Streamlit.
- On confirm, crop the original image to the user's selected region, then resize
  that cropped region to exactly 1400x840px using high-quality resampling
  (e.g. Lanczos). No stretching or distortion — the aspect ratio lock in the
  previous step guarantees this resize is proportional.

### 4. Overlay compositing
- After the crop is finalized, the user picks **one** bundled overlay via
  exclusive checkboxes. Checking a variant updates the live preview immediately:
  - `overlay` (`assets/overlay.svg`) — full brand overlay (scrim + swooshes)
  - `overlay_ai` (`assets/overlay_ai.svg`) — brand overlay plus AI badge
  - `overlay_ai_only` (`assets/overlay_ai_only.svg`) — AI badge only
  - `no overlay` — photo only (rounded corners still applied)
- Overlay position: anchored at (0, 0), scaled to match the full 1400x840 canvas
  exactly (the overlay's own design already defines where its shapes, gradients,
  and rounded-corner clip-path sit within that canvas — do not add any additional
  masking, opacity, or repositioning logic beyond what the SVG itself specifies).
- The base photo must remain fully visible/unaltered beneath the overlay except
  where the overlay's own alpha channel makes it semi-transparent or opaque, per
  its original design.

### 5. Rounded corners
- `overlay.svg` defines a rounded-rectangle clip-path for the whole canvas.
  Every variant uses that same clip when compositing — including `overlay_ai_only`,
  which has no clip-path of its own — so corners stay transparent PNG, not square.
- Output format must support transparency (PNG) to preserve this, since the
  rounded corners can't be represented in a JPEG.

### 6. Headline text
- After crop + overlay, overlay editable headline text on the live preview.
- Default copy: `insert your text here`.
- Default position: bottom-left, **64px** from the left edge and **48px** from
  the bottom edge of the 1400x840 canvas. Until the user drags, extra lines grow
  upward so that bottom padding stays 48px.
- Typography (live preview and export must match):
  - color: white
  - font-size: 95px
  - font-family: Gilroy
  - font-weight: 700
  - line-height: 112px
  - word-wrap: break-word
  - White border while the headline is selected/editing; no border when
    deselected. Idle preview shows the baked PNG so it matches export.
- Render with the bundled file `assets/fonts/EurowingsWeb-Bold.ttf` (Eurowings
  Gilroy Bold cut).
- The manager can **drag** the text to reposition it and **edit copy inline**.
- The manager can **delete the headline**. Export then omits text (crop + overlay
  only). Headline can be added back in the same session.
- When a headline is present, export bakes it into the final PNG at that
  position. The download includes crop + overlay, and text only if it was kept.

### 7. Output
- Final exported image: exactly 1400x840px, PNG, with the chosen overlay applied,
  optional headline baked in, and rounded corners preserved.
- Provide a download button for the user to save the result.
- (Nice-to-have, not required for v1): warn or auto-compress if file size exceeds
  5MB, matching the export constraint used elsewhere in this org's image tooling.

---

## Suggested tech stack

- **Framework:** Streamlit (Python)
- **Image processing:** Pillow (PIL), NumPy
- **SVG rendering:** resvg (no system Cairo library; Streamlit Cloud compatible)
- **Interactive cropping:** streamlit-cropper (or equivalent Streamlit-compatible
  cropping component)
- **Headline UI:** Streamlit custom component (contenteditable + drag) over the
  composed preview

## Suggested file structure

```
watermark-app/
├── app.py                       # Streamlit entrypoint
├── assets/
│   ├── overlay.svg              # full brand overlay
│   ├── overlay_ai.svg           # brand overlay + AI badge
│   └── overlay_ai_only.svg      # AI badge only
│   └── fonts/
│       └── EurowingsWeb-Bold.ttf
├── components/
│   └── headline/                # live drag + inline-edit headline
├── lib/
│   ├── overlay.py               # SVG rendering + caching
│   ├── crop.py                  # crop UI + crop/resize logic
│   ├── headline.py              # wrap + bake text into PNG
│   └── compose.py               # compositing + rounded-corner handling
├── requirements.txt
├── Dockerfile
└── AGENTS.md
```

## Explicit non-goals for this version

- No generative AI / AI image models anywhere in this pipeline — this app exists
  specifically because generative tools (e.g. Copilot Designer) could not
  reproduce the overlay's exact shapes, opacity, and corners reliably. Every step
  here must be deterministic.
- No batch processing in v1 — single image in, single image out, per session.

## Validation checklist before considering this done

- [ ] Same input image + same crop selection + same headline always produces
      byte-identical output
- [ ] Overlay scrim/shadow gradient and magenta swooshes both render from the
      SVG (no color-detection/heuristic background removal)
- [ ] Overlay gradients and rounded corners match the source SVG exactly
- [ ] Cropping never distorts the image (aspect ratio always 5:3 going in)
- [ ] Output is always exactly 1400x840px
- [ ] Output file supports transparency (rounded corners render correctly, not as
      white/black squares)
- [ ] Headline uses EurowingsWeb-Bold.ttf at 95px / 112px line-height, white,
      break-word wrap; default copy, 64px left and 48px bottom padding; drag + inline
      edit with a white selection border; optional delete so export can omit text;
      baked into the downloaded PNG when kept
- [ ] Overlay variant checkboxes (`overlay`, `overlay_ai`, `overlay_ai_only`, `no overlay`)
      are exclusive and update the live preview immediately
