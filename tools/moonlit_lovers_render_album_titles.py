#!/usr/bin/env python3
"""Render the album's category titles, the row-of-bubbles plates in GADAT032.

``dat/gadat032/アルバム/gxttlN1.tex`` holds one album category name as a row of speech-bubble
tiles, one per Japanese character.  Seven of the eight had already been translated, but those
renders replaced the source's alpha with a solid one, so each plate would show as an opaque
black rectangle over the album screen, and two of them repeated their last syllable on a tile
that should have stayed empty.  ``gxttl21`` had never been translated at all.

The plates are drawn as a soft glow rather than as crisp type: a bubble is a flat fill inside a
bright outline, with the character glowing in the middle.  Most of them carry that glow in the
alpha channel over a flat colour; ``gxttl91`` carries it in the colour over a plain silhouette.
Either way the render keeps the bubbles exactly as they are, flattens the character back to the
bubble's own fill, and draws the Korean syllable at the same softness.

A syllable never lands on a small kana tile — the long-vowel bar of ミルフィーユ or the ォ of
フォルテ — so those tiles are left empty, as the album's own typography does.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")

# name -> (Japanese, one entry per bubble; "" leaves that bubble empty, channel carrying the glow)
GROUPS: dict[str, tuple[str, list[str], str]] = {
    "gxttl21.tex": ("シーン選択", ["장", "", "면", "선", "택"], "alpha"),
    "gxttl31.tex": ("その他", ["기", "", "타"], "alpha"),
    "gxttl41.tex": ("ミルフィーユ", ["밀", "", "피", "", "", "유"], "alpha"),
    "gxttl51.tex": ("ランファ", ["란", "", "파", ""], "alpha"),
    "gxttl61.tex": ("ミント", ["민", "", "트"], "alpha"),
    "gxttl71.tex": ("フォルテ", ["포", "", "르", "테"], "alpha"),
    "gxttl81.tex": ("ヴァニラ", ["바", "", "닐", "라"], "alpha"),
    "gxttl91.tex": ("ちとせ", ["치", "토", "세"], "luminance"),
}


def boxes_from(labels: np.ndarray, count: int) -> list[tuple[int, int, int, int]]:
    found = []
    for index in range(1, count):
        ys, xs = np.where(labels == index)
        if len(ys) < 120:
            continue
        found.append((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    # A character that separates from its bubble shows up as a box inside another one.
    found.sort(key=lambda box: (box[2] - box[0]) * (box[3] - box[1]), reverse=True)
    kept: list[tuple[int, int, int, int]] = []
    for box in found:
        if any(o[0] <= box[0] and o[1] <= box[1] and o[2] >= box[2] and o[3] >= box[3] for o in kept):
            continue
        kept.append(box)
    return sorted(kept, key=lambda box: box[0])


def bubbles(mask: np.ndarray, expected: int, values: np.ndarray | None = None) -> list[tuple[int, int, int, int]]:
    """Find each speech bubble, splitting ones that touch.

    Most plates leave a gap between bubbles, so labelling the shape is enough.  Where they
    overlap, the centre of each bubble is still the point furthest from the outside, so the
    peaks of a distance transform seed a watershed that cuts them apart.
    """
    shape = mask.astype(np.uint8)
    count, labels = cv2.connectedComponents(shape, 8)
    found = boxes_from(labels, count)
    if len(found) >= expected:
        return found

    distance = cv2.distanceTransform(shape, cv2.DIST_L2, 5)
    _, peaks = cv2.threshold(distance, 0.55 * distance.max(), 255, cv2.THRESH_BINARY)
    seed_count, seeds = cv2.connectedComponents(peaks.astype(np.uint8), 8)
    markers = seeds.astype(np.int32) + 1
    markers[shape == 0] = 1
    # The watershed needs something with edges to flow along; a flat mask gives it nothing, so
    # the picture itself is what the bubbles are cut apart on.
    guide = (shape * 255) if values is None else np.clip(values, 0, 255).astype(np.uint8)
    colour = cv2.cvtColor(guide, cv2.COLOR_GRAY2BGR)
    cv2.watershed(colour, markers)
    split = np.where(markers > 1, markers - 1, 0)
    return boxes_from(split, seed_count)


def fit_font(text: str, width: int, height: int) -> ImageFont.FreeTypeFont:
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    for size in range(height + 4, 6, -1):
        font = ImageFont.truetype(str(FONT_BOLD), size=size)
        box = probe.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= width and box[3] - box[1] <= height:
            return font
    return ImageFont.truetype(str(FONT_BOLD), size=7)


def bands(boxes: list[tuple[int, int, int, int]], width: int) -> list[tuple[int, int]]:
    """Cut the plate into one vertical strip per bubble.

    The bubbles' soft outer glow overlaps, so the silhouette is a single blob and cannot be
    labelled bubble by bubble.  They are far enough apart at the level the glow does not reach,
    though, so the midpoints between those cores say where one bubble's strip ends and the
    next begins — and the cut always falls in the dim gap between two bubbles.
    """
    cuts = [0]
    for left, right in zip(boxes, boxes[1:]):
        cuts.append((left[2] + right[0]) // 2)
    cuts.append(width)
    return list(zip(cuts, cuts[1:]))


def redraw(values: np.ndarray, shape: np.ndarray, syllables: list[str],
           split: np.ndarray | None = None) -> np.ndarray:
    """Replace the character glowing inside each bubble with a Korean syllable."""
    cores = bubbles(shape if split is None else split, len(syllables), values)
    if len(cores) != len(syllables):
        raise SystemExit(f"expected {len(syllables)} bubbles, found {len(cores)}")
    plate = values.astype(np.float32).copy()
    glow = np.zeros(values.shape, dtype=np.float32)
    peaks = []
    for (core, (begin, end)), syllable in zip(zip(cores, bands(cores, values.shape[1])), syllables):
        strip = np.zeros(shape.shape, dtype=np.uint8)
        strip[:, begin:end] = shape[:, begin:end]
        # Distance from the bubble's own edge separates its outline from its inside far more
        # reliably than brightness does: the outline and the brightest strokes of the character
        # reach the same level.
        depth = cv2.distanceTransform(strip, cv2.DIST_L2, 3)
        # Two pixels of outline is what these bubbles are drawn with; keeping three leaves the
        # tail of a character that runs close to the rim standing outside the repaint.
        interior = depth >= 2
        if not interior.any():
            continue
        # The fill is what the ring just inside the outline sits at; the character glows
        # further in, so that ring is the flat colour and nothing else.
        ring = interior & (depth <= 4)
        fill = float(np.median(values[ring])) if ring.any() else float(np.median(values[interior]))
        character = interior & (values > fill + 10)
        if character.any():
            peaks.append(float(values[character].max()))
        plate[interior] = fill
        if not syllable:
            continue
        # The syllable is placed against the bubble itself, not against the core the split was
        # seeded from: on a plate whose bubbles overlap, that core is only their centre and
        # sizing type to it leaves a speck in the middle of a full-size bubble.
        rows_here, columns_here = np.where(interior)
        left, top = int(columns_here.min()), int(rows_here.min())
        right, bottom = int(columns_here.max()) + 1, int(rows_here.max()) + 1
        width, height = right - left, bottom - top
        font = fit_font(syllable, int(width * 0.74), int(height * 0.64))
        canvas = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(canvas)
        box = draw.textbbox((0, 0), syllable, font=font)
        draw.text((round(width / 2 - (box[2] - box[0]) / 2 - box[0]),
                   round(height / 2 - (box[3] - box[1]) / 2 - box[1])),
                  syllable, font=font, fill=255)
        drawn = np.zeros(values.shape, dtype=np.float32)
        drawn[top:bottom, left:right] = np.array(canvas, dtype=np.float32)
        drawn[~interior] = 0.0
        glow = np.maximum(glow, drawn)

    glow = cv2.GaussianBlur(glow, (0, 0), 1.1)
    # The syllable has to read as brightly as the character it replaces, so the brightest of
    # them sets the level rather than the middling one.
    peak = float(max(peaks)) if peaks else 255.0
    out = np.clip(np.maximum(plate, glow / 255.0 * peak), 0, 255)
    out[~shape] = 0
    return out


def render(source: Path, syllables: list[str], carrier: str) -> Image.Image:
    original = Image.open(source).convert("RGBA")
    arr = np.array(original)
    rgb, alpha = arr[:, :, :3], arr[:, :, 3]
    shape = alpha > 16
    if carrier == "alpha":
        # The bubbles' outer glow overlaps, so the silhouette is one blob; the bubbles only
        # come apart above the level that glow reaches.
        drawn = redraw(alpha, shape, syllables, split=alpha > 60)
        return Image.fromarray(np.dstack([rgb, drawn.astype(np.uint8)]), "RGBA")

    # The colour carries the glow here and the alpha is a plain silhouette, so the plate is
    # redrawn in brightness and the bubble's own hue is put back over it.
    luminance = rgb.astype(np.float32).mean(axis=2)
    lit = shape & (luminance > 1)
    hue = np.median(rgb[lit].astype(np.float32) / luminance[lit][:, None], axis=0)
    out = redraw(luminance, shape, syllables)
    tinted = np.clip(out[:, :, None] * hue[None, None, :], 0, 255).astype(np.uint8)
    tinted[~shape] = 0
    return Image.fromarray(np.dstack([tinted, alpha]), "RGBA")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=Path("work/galaxy_angel_moonlit_lovers"))
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--only", action="append", default=None)
    args = parser.parse_args()

    resources = {
        r["name"]: r
        for r in json.loads(
            (args.project / "assets/full_extraction/GADAT032/manifest.json").read_text(encoding="utf-8")
        )["resources"]
        if r.get("name")
    }
    images_root = args.project / "assets/image_extraction/GADAT032/japanese_images"
    written = []
    for name, (japanese, syllables, carrier) in GROUPS.items():
        if args.only and name not in args.only:
            continue
        png = f"block_{int(resources[name]['offset']):08x}.png"
        image = render(images_root / "png" / png, syllables, carrier)
        target = args.preview or (images_root / "translated_png")
        target.mkdir(parents=True, exist_ok=True)
        image.save(target / png)
        written.append({"name": name, "png": png, "japanese": japanese,
                        "korean": "".join(syllables), "carrier": carrier})
    print(json.dumps({"written": written}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
