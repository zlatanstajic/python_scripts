#!/usr/bin/env python3
"""Generate the 1200x630 Open Graph image for Python Scripts.

The output is deterministic given the same installed TrueType fonts: there is
no randomness or timestamp. Font resolution uses fixed candidate lists and
fails loudly instead of falling back to Pillow's low-resolution default.

Run from the repository root:
    python tools/gen-og-image.py
Output: assets/img/og-image.png
"""

import os

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1200, 630
BACKGROUND = (15, 23, 42)
PANEL = (31, 41, 55)
BORDER = (62, 62, 58)
PYTHON_BLUE = (55, 118, 171)
PYTHON_YELLOW = (255, 212, 59)
TEXT = (240, 246, 252)
MUTED = (139, 148, 158)
RED = (255, 95, 86)
YELLOW = (255, 189, 46)
GREEN = (39, 201, 63)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "assets", "img", "og-image.png")


def load_font(size, monospace=False):
    """Load a bold TrueType font from a fixed candidate list."""
    if monospace:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        ]

    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    font_kind = "bold monospace" if monospace else "bold sans"
    raise RuntimeError(
        "No "
        + font_kind
        + " TrueType font found; looked in:\n  "
        + "\n  ".join(candidates)
    )


def centered_x(draw, text, font):
    """Return the x coordinate that horizontally centers text."""
    bounds = draw.textbbox((0, 0), text, font=font)
    return (WIDTH - (bounds[2] - bounds[0])) // 2 - bounds[0]


def main():
    """Render and save the social-preview image."""
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    left, top, right, bottom = 210, 72, 990, 350
    draw.rounded_rectangle(
        [left, top, right, bottom],
        radius=26,
        fill=PANEL,
        outline=BORDER,
        width=3,
    )
    draw.line([left, top + 62, right, top + 62], fill=BORDER, width=3)

    dot_y = top + 31
    for dot_x, color in (
        (left + 34, RED),
        (left + 67, YELLOW),
        (left + 100, GREEN),
    ):
        draw.ellipse(
            [dot_x - 9, dot_y - 9, dot_x + 9, dot_y + 9],
            fill=color,
        )

    prompt_font = load_font(42, monospace=True)
    draw.text((left + 52, top + 99), ">>>", font=prompt_font, fill=PYTHON_YELLOW)
    draw.text(
        (left + 164, top + 99),
        "python scripts/",
        font=prompt_font,
        fill=TEXT,
    )

    utility_font = load_font(27, monospace=True)
    utility_text = "cv_generator.py  |  screenshot.py"
    draw.text(
        (left + 52, top + 181),
        utility_text,
        font=utility_font,
        fill=MUTED,
    )

    title_font = load_font(82)
    title = "Python Scripts"
    title_bounds = draw.textbbox((0, 0), title, font=title_font)
    title_y = 390 - title_bounds[1]
    draw.text(
        (centered_x(draw, title, title_font), title_y),
        title,
        font=title_font,
        fill=TEXT,
    )

    tagline_font = load_font(36)
    tagline = "Practical Python tools for documents and the web"
    tagline_bounds = draw.textbbox((0, 0), tagline, font=tagline_font)
    tagline_y = 500 - tagline_bounds[1]
    draw.text(
        (centered_x(draw, tagline, tagline_font), tagline_y),
        tagline,
        font=tagline_font,
        fill=PYTHON_BLUE,
    )

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    image.save(OUTPUT_PATH, "PNG", optimize=True)
    print("wrote", OUTPUT_PATH, image.size)


if __name__ == "__main__":
    main()
