"""Generate the OG image for the marketing site.

Composes a 1200x630 social card with the Primer wordmark, tagline,
demo CTA, and an inset of the dashboard screenshot.

Run when the dashboard screenshot or branding changes:

    python scripts/generate_og_image.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
WEBSITE_PUBLIC = REPO_ROOT / "website" / "public"
SOURCE_SCREENSHOT = WEBSITE_PUBLIC / "screenshots" / "readme-dashboard-dark.png"
OUTPUT_PATH = WEBSITE_PUBLIC / "og-image.png"

# Brand colors pulled from the site's hero gradient
BG_COLOR = (10, 12, 24)  # near-black
BG_GRADIENT_COLOR = (24, 27, 60)
ACCENT = (129, 140, 248)  # primer-400
TEXT_PRIMARY = (255, 255, 255)
TEXT_MUTED = (180, 188, 218)
TEXT_DIM = (120, 130, 165)

WIDTH = 1200
HEIGHT = 630


def _font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    """Load a system font, honoring the requested weight.

    .ttc TrueType Collections pack multiple faces under different indices
    and Pillow's truetype() defaults to index 0 (regular). To actually get
    a bold face we have to enumerate indices and pick the one whose
    PostScript name contains 'Bold'.
    """
    candidates = [
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for path in candidates:
        if not Path(path).exists():
            continue
        if weight == "bold":
            for index in range(12):
                try:
                    font = ImageFont.truetype(path, size, index=index)
                except OSError:
                    break
                _, style = font.getname()
                if "bold" in (style or "").lower() and "italic" not in (style or "").lower():
                    return font
            # No bold face found in this collection — fall through to next
            continue
        try:
            return ImageFont.truetype(path, size, index=0)
        except OSError:
            continue
    # Fallback: Pillow 10.1+ accepts size; older versions ignore the kwarg.
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _radial_background(width: int, height: int) -> Image.Image:
    """Create a dark background with a soft radial highlight in the top-left."""
    bg = Image.new("RGB", (width, height), BG_COLOR)
    pixels = bg.load()
    cx, cy = width * 0.25, height * 0.15
    max_r = (width**2 + height**2) ** 0.5
    for y in range(height):
        for x in range(0, width, 4):  # stride for speed
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            t = max(0.0, 1.0 - d / (max_r * 0.55))
            r = int(BG_COLOR[0] + (BG_GRADIENT_COLOR[0] - BG_COLOR[0]) * t)
            g = int(BG_COLOR[1] + (BG_GRADIENT_COLOR[1] - BG_COLOR[1]) * t)
            b = int(BG_COLOR[2] + (BG_GRADIENT_COLOR[2] - BG_COLOR[2]) * t)
            for dx in range(4):
                if x + dx < width:
                    pixels[x + dx, y] = (r, g, b)
    return bg


def main() -> int:
    if not SOURCE_SCREENSHOT.exists():
        print(f"Missing source screenshot at {SOURCE_SCREENSHOT}", file=sys.stderr)
        return 1

    canvas = _radial_background(WIDTH, HEIGHT)
    draw = ImageDraw.Draw(canvas)

    # Eyebrow
    eyebrow = "OPEN SOURCE  •  WORKFLOW INTELLIGENCE"
    eyebrow_font = _font(20)
    draw.text((64, 80), eyebrow, font=eyebrow_font, fill=ACCENT)

    # Headline (two lines)
    headline_font = _font(56, weight="bold")
    draw.text((64, 130), "See which AI workflows", font=headline_font, fill=TEXT_PRIMARY)
    draw.text((64, 200), "actually work.", font=headline_font, fill=ACCENT)

    # Subtitle
    subtitle_font = _font(22)
    draw.text(
        (64, 290),
        "Workflow fingerprints, quality attribution,",
        font=subtitle_font,
        fill=TEXT_MUTED,
    )
    draw.text(
        (64, 322),
        "cost proof, and experiments for agentic teams.",
        font=subtitle_font,
        fill=TEXT_MUTED,
    )

    # CTA pill
    pill_font = _font(22, weight="bold")
    pill_text = "demo.useprimer.dev →"
    pill_w = int(draw.textlength(pill_text, font=pill_font)) + 48
    pill_x, pill_y = 64, 430
    pill_h = 56
    draw.rounded_rectangle(
        (pill_x, pill_y, pill_x + pill_w, pill_y + pill_h),
        radius=28,
        fill=(ACCENT[0], ACCENT[1], ACCENT[2], 255),
    )
    draw.text(
        (pill_x + 24, pill_y + 14),
        pill_text,
        font=pill_font,
        fill=BG_COLOR,
    )

    # Footer mark
    footer_font = _font(18)
    draw.text(
        (64, 540),
        "primer  ·  open source  ·  self-hosted",
        font=footer_font,
        fill=TEXT_DIM,
    )

    # Inset screenshot, bottom-right, smaller so the headline isn't clipped
    shot = Image.open(SOURCE_SCREENSHOT).convert("RGB")
    shot_w = 380
    aspect = shot.height / shot.width
    shot_h = int(shot_w * aspect)
    shot_resized = shot.resize((shot_w, shot_h), Image.LANCZOS)
    shot_x = WIDTH - shot_w - 64
    shot_y = HEIGHT - shot_h - 96
    # subtle border
    border_pad = 6
    draw.rounded_rectangle(
        (
            shot_x - border_pad,
            shot_y - border_pad,
            shot_x + shot_w + border_pad,
            shot_y + shot_h + border_pad,
        ),
        radius=14,
        fill=(40, 46, 80),
    )
    canvas.paste(shot_resized, (shot_x, shot_y))

    canvas.save(OUTPUT_PATH, "PNG", optimize=True)
    print(f"Wrote {OUTPUT_PATH} ({WIDTH}x{HEIGHT})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
