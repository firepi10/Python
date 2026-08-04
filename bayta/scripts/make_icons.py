#!/usr/bin/env python3
"""Generate the Bayta app icons (PWA + apple-touch-icon).

A minimal white house glyph — 'bayta' is Aramaic for house — on an
iOS-blue-to-indigo gradient. Pure PIL, no font dependencies.
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "frontend" / "public" / "icons"

TOP = (10, 132, 255)  # iOS blue
BOTTOM = (94, 92, 230)  # iOS indigo


def gradient(size: int) -> Image.Image:
    img = Image.new("RGB", (size, size))
    d = ImageDraw.Draw(img)
    for y in range(size):
        t = y / size
        d.line(
            [(0, y), (size, y)],
            fill=tuple(int(a + (b - a) * t) for a, b in zip(TOP, BOTTOM, strict=True)),
        )
    return img


def rounded(img: Image.Image, radius_frac: float) -> Image.Image:
    size = img.width
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size, size], radius=int(size * radius_frac), fill=255
    )
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def draw_house(img: Image.Image) -> None:
    s = img.width
    d = ImageDraw.Draw(img)
    white = (255, 255, 255)

    roof_apex = (s * 0.50, s * 0.24)
    roof_l = (s * 0.20, s * 0.52)
    roof_r = (s * 0.80, s * 0.52)
    d.polygon([roof_l, roof_apex, roof_r], fill=white)

    body_l, body_r = s * 0.28, s * 0.72
    body_top, body_bottom = s * 0.50, s * 0.76
    d.rounded_rectangle([body_l, body_top, body_r, body_bottom], radius=int(s * 0.02), fill=white)

    # door in gradient color (sampled mid-body)
    door_color = img.getpixel((int(s * 0.5), int(s * 0.64)))
    dw = s * 0.10
    d.rounded_rectangle(
        [s * 0.5 - dw / 2, s * 0.60, s * 0.5 + dw / 2, body_bottom],
        radius=int(s * 0.035),
        fill=door_color,
    )


def make(size: int, path: Path, round_corners: bool) -> None:
    img = gradient(size)
    draw_house(img)
    final = rounded(img, 0.225) if round_corners else img.convert("RGBA")
    OUT.mkdir(parents=True, exist_ok=True)
    final.save(path)
    print("wrote", path.relative_to(OUT.parents[2]))


if __name__ == "__main__":
    make(512, OUT / "icon-512.png", round_corners=True)
    make(192, OUT / "icon-192.png", round_corners=True)
    # iOS applies its own mask — ship square
    make(180, OUT / "apple-touch-icon.png", round_corners=False)
    sys.exit(0)
