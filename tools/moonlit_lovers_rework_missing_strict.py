#!/usr/bin/env python3
"""Strict rework of user-deleted Moonlit Lovers localized PNGs.

Authority is japanese_images/png.  Only a source PNG that still exists there and
has no translated_png peer is regenerated.  Nothing ever repopulates a source
PNG deleted by the user.

Policy: replace Japanese glyphs only; preserve every pixel outside the approved
source-text region byte-for-byte.  English, numbers, icons and other artwork are
not translation targets.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import moonlit_lovers_render_gadat032_ui as ml

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "work/galaxy_angel_moonlit_lovers"
MANUAL_AUTHORITY = PROJECT / "assets/image_extraction/manual_translated_png_authority.json"
FONT_UI = Path("C:/Windows/Fonts/H2GTRM.TTF")
FONT_TITLE = Path("C:/Windows/Fonts/malgunbd.ttf")

STRICT_POLICY = {
    "authority": "japanese_images/png",
    "only_regenerate_missing_translated_png": True,
    "translate_japanese_only": True,
    "preserve_non_japanese_text": True,
    "outside_approved_text_region_changed_pixels_required": 0,
    "preserve_resolution": True,
    "preserve_layout": True,
    "preserve_ui_icons_background_artwork": True,
}


def rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def fit_font(text: str, font_path: Path, max_size: int, min_size: int, width: int, height: int) -> ImageFont.FreeTypeFont:
    probe = Image.new("L", (max(8, width * 2), max(8, height * 2)), 0)
    draw = ImageDraw.Draw(probe)
    for size in range(max_size, min_size - 1, -1):
        f = ImageFont.truetype(str(font_path), size=size)
        b = draw.textbbox((0, 0), text, font=f, stroke_width=0)
        if b[2] - b[0] <= width and b[3] - b[1] <= height:
            return f
    return ImageFont.truetype(str(font_path), size=min_size)


def source_mask(image: Image.Image, box: tuple[int, int, int, int] | None, *, saturated: bool = False) -> np.ndarray:
    arr = np.array(image, dtype=np.uint8)
    rgb = arr[:, :, :3].astype(np.int16)
    alpha = arr[:, :, 3]
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    if box is None:
        region = np.ones(alpha.shape, bool)
    else:
        l, t, r, b = box
        region = np.zeros(alpha.shape, bool)
        region[max(0, t):min(image.height, b), max(0, l):min(image.width, r)] = True
    neutral = (alpha > 45) & (mx > 125) & ((mx - mn) < 150)
    bright = (alpha > 45) & (mx > 175)
    mask = (neutral | (bright if saturated else False)) & region
    mask_u8 = mask.astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask_u8, 8)
    kept = np.zeros_like(mask)
    for idx in range(1, count):
        x, y, w, h, area = [int(v) for v in stats[idx]]
        if area < 2:
            continue
        if w > image.width * 0.92 and h <= 3:
            continue
        if box is None and (x <= 1 or y <= 1 or x + w >= image.width - 1 or y + h >= image.height - 1) and area > 40:
            continue
        kept[labels == idx] = True
    if kept.any():
        mask = kept
    return mask


def score_name_mask(image: Image.Image) -> np.ndarray:
    """Isolate only the stylized Japanese score-name glyphs.

    The b/f button states use different foreground colours.  The old cyan-only
    detector therefore fell back to a very broad 275px mask on several images,
    inpainting UI artwork together with the name.  Build candidates from both
    colour and neutral text masks, but only keep connected components in the
    left-side name lane.  Never fall back to the full decorated band.
    """
    arr = np.array(image, dtype=np.uint8)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    alpha = arr[:, :, 3]
    yy, xx = np.indices(alpha.shape)
    lane = (
        (yy < min(50, image.height))
        & (xx >= 90)
        & (xx < min(275, image.width))
    )
    cyan_or_white = (
        ((b > 175) & (g > 120) & (r < 145))
        | ((r > 215) & (g > 215) & (b > 215))
    )
    rgb = arr[:, :, :3].astype(np.int16)
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    neutral = (alpha > 45) & (mx > 125) & ((mx - mn) < 150)
    masks = [(alpha > 110) & cyan_or_white & lane, neutral & lane]
    kept = np.zeros(alpha.shape, bool)
    for raw in masks:
        count, labels, stats, _ = cv2.connectedComponentsWithStats(
            raw.astype(np.uint8), 8
        )
        for idx in range(1, count):
            x, y, w, h, area = [int(v) for v in stats[idx]]
            if (
                area >= 15
                and x >= 90
                and x < 270
                and y <= 30
                and 4 <= w <= 190
                and h >= 5
            ):
                kept[labels == idx] = True
    if not kept.any():
        raise ValueError("could not isolate score-name glyphs without touching artwork")
    return kept


def glyph_bbox(mask: np.ndarray, fallback: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return fallback
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def sample_style(image: Image.Image, mask: np.ndarray) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    arr = np.array(image, dtype=np.uint8)
    pix = arr[mask]
    if not len(pix):
        return (235, 235, 235), (245, 245, 245), (80, 80, 80)
    val = pix[:, :3].mean(axis=1)
    lo = pix[val <= np.percentile(val, 20), :3]
    hi = pix[val >= np.percentile(val, 82), :3]
    mid_hi = pix[val >= np.percentile(val, 55), :3]
    mid = pix[:, :3]
    top = np.median(hi if len(hi) else mid, axis=0).astype(int)
    bottom = np.median(mid_hi if len(mid_hi) else mid, axis=0).astype(int)
    dark = np.median(lo if len(lo) else mid, axis=0).astype(int)
    return tuple(map(int, top)), tuple(map(int, bottom)), tuple(map(int, dark))


def clean_masked(image: Image.Image, mask: np.ndarray, *, dilation: int = 1, clip_box: tuple[int, int, int, int] | None = None) -> tuple[Image.Image, np.ndarray]:
    if not mask.any():
        return image.copy(), mask
    m = mask.astype(np.uint8)
    if dilation:
        m = cv2.dilate(m, np.ones((3, 3), np.uint8), iterations=dilation)
    if clip_box is not None:
        l, t, r, b = clip_box
        clip = np.zeros_like(m)
        clip[max(0, t):min(image.height, b), max(0, l):min(image.width, r)] = 1
        m &= clip
    # Preserve alpha and only reconstruct RGB underneath the source glyph pixels.
    arr = np.array(image, dtype=np.uint8)
    rgb = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2BGR)
    restored = cv2.inpaint(rgb, (m * 255).astype(np.uint8), 2, cv2.INPAINT_TELEA)
    out = arr.copy()
    out[:, :, :3] = cv2.cvtColor(restored, cv2.COLOR_BGR2RGB)
    return Image.fromarray(out, "RGBA"), m.astype(bool)


def draw_styled(image: Image.Image, text: str, target: tuple[int, int, int, int], style_source: Image.Image, style_mask: np.ndarray, *, font_path: Path = FONT_UI, max_size: int = 28, min_size: int = 6, stroke: int | None = None, glow: bool = False, flat_bright: bool = False) -> tuple[Image.Image, np.ndarray]:
    if not text:
        return image, np.zeros((image.height, image.width), bool)
    l, t, r, b = target
    width = max(4, r - l); height = max(4, b - t)
    f = fit_font(text, font_path, max_size, min_size, max(3, width - 2), max(3, height - 1))
    probe = Image.new("L", image.size, 0)
    pd = ImageDraw.Draw(probe)
    tb = pd.textbbox((0, 0), text, font=f)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    x = round((l + r) / 2 - tw / 2 - tb[0])
    y = round((t + b) / 2 - th / 2 - tb[1])
    source_h = max(1, glyph_bbox(style_mask, target)[3] - glyph_bbox(style_mask, target)[1])
    sw = (1 if source_h >= 13 else 0) if stroke is None else stroke
    x = max(l + sw - tb[0], min(x, r - sw - tb[2]))
    y = max(t + sw - tb[1], min(y, b - sw - tb[3]))
    fill_mask = Image.new("L", image.size, 0)
    fd = ImageDraw.Draw(fill_mask)
    fd.text((x, y), text, font=f, fill=255)
    stroke_mask = Image.new("L", image.size, 0)
    sd = ImageDraw.Draw(stroke_mask)
    sd.text((x, y), text, font=f, fill=255, stroke_width=sw, stroke_fill=255)
    fill_np = np.array(fill_mask) > 0
    stroke_np = (np.array(stroke_mask) > 0) & ~fill_np

    top, bottom, dark = sample_style(style_source, style_mask)
    if flat_bright:
        bottom = top
    arr = np.array(image, dtype=np.uint8)
    if glow:
        raw = np.array(stroke_mask, dtype=np.uint8)
        blurred = cv2.GaussianBlur(raw, (0, 0), 1.15)
        ga = np.minimum(95, (blurred.astype(np.float32) * 0.38)).astype(np.uint8)
        glow_np = (ga > 3) & ~fill_np & ~stroke_np
        if glow_np.any():
            yy, xx = np.where(glow_np)
            amt = (ga[yy, xx].astype(np.float32) / 255.0)[:, None]
            arr[yy, xx, :3] = np.clip(arr[yy, xx, :3].astype(np.float32) * (1.0 - amt) + np.array(top, dtype=np.float32) * amt, 0, 255).astype(np.uint8)
            arr[yy, xx, 3] = np.maximum(arr[yy, xx, 3], ga[yy, xx])
    if fill_np.any():
        ys = np.arange(image.height, dtype=np.float32)
        denom = max(1.0, float(b - t - 1))
        amount = np.clip((ys - t) / denom, 0, 1)[:, None]
        grad = np.empty((image.height, 3), dtype=np.float32)
        for c in range(3):
            grad[:, c] = top[c] * (1.0 - amount[:, 0]) + bottom[c] * amount[:, 0]
        yy, xx = np.where(fill_np)
        arr[yy, xx, :3] = np.clip(grad[yy], 0, 255).astype(np.uint8)
        arr[yy, xx, 3] = 255
    if sw and stroke_np.any():
        yy, xx = np.where(stroke_np)
        arr[yy, xx, :3] = np.array(dark, dtype=np.uint8)
        arr[yy, xx, 3] = np.maximum(arr[yy, xx, 3], 220)
    return Image.fromarray(arr, "RGBA"), (fill_np | stroke_np)


def replace_region_expanded(original: Image.Image, text: str, mask_box: tuple[int, int, int, int], draw_box: tuple[int, int, int, int], *, saturated: bool = False, font_path: Path = FONT_UI, max_size: int = 28, min_size: int = 6, stroke: int | None = None, glow: bool = False, flat_bright: bool = False) -> tuple[Image.Image, np.ndarray]:
    mask = source_mask(original, mask_box, saturated=saturated)
    cleaned, _ = clean_masked(original, mask, dilation=1, clip_box=mask_box)
    rendered, _ = draw_styled(cleaned, text, draw_box, original, mask, font_path=font_path, max_size=max_size, min_size=min_size, stroke=stroke, glow=glow, flat_bright=flat_bright)
    allowed = np.zeros((original.height, original.width), bool)
    for l,t,r,b in (mask_box, draw_box):
        allowed[max(0,t):min(original.height,b),max(0,l):min(original.width,r)] = True
    return rendered, allowed


def replace_region(original: Image.Image, text: str, box: tuple[int, int, int, int], *, saturated: bool = False, font_path: Path = FONT_UI, max_size: int = 28, min_size: int = 6, special_mask: np.ndarray | None = None) -> tuple[Image.Image, np.ndarray]:
    mask = special_mask if special_mask is not None else source_mask(original, box, saturated=saturated)
    gb = glyph_bbox(mask, box)
    cleaned, removed = clean_masked(original, mask, dilation=1, clip_box=box)
    target = gb
    rendered, added = draw_styled(cleaned, text, target, original, mask, font_path=font_path, max_size=max_size, min_size=min_size)
    allowed = np.zeros((original.height, original.width), bool)
    l, t, r, b = box
    allowed[max(0, t):min(original.height, b), max(0, l):min(original.width, r)] = True
    return rendered, allowed


def render_text_only(original: Image.Image, text: str, *, font_path: Path = FONT_TITLE, glow: bool = True, flat_bright: bool = False) -> tuple[Image.Image, np.ndarray]:
    alpha = np.array(original.getchannel("A")) > 0
    mask = source_mask(original, None, saturated=False)
    style_mask = mask if mask.any() else alpha
    core = glyph_bbox(style_mask, original.getchannel("A").getbbox() or (0,0,original.width,original.height))
    # Keep a small effect margin but do not use the whole canvas as the glyph height.
    box = (max(0,core[0]-3),max(0,core[1]-2),min(original.width,core[2]+3),min(original.height,core[3]+2))
    canvas = Image.new("RGBA", original.size, (0, 0, 0, 0))
    rendered, _ = draw_styled(canvas, text, box, original, style_mask, font_path=font_path, max_size=min(26,max(12, box[3]-box[1]+3)), min_size=6, stroke=1, glow=glow, flat_bright=flat_bright)
    allowed = np.zeros((original.height, original.width), bool)
    l, t, r, b = box
    allowed[t:b, l:r] = True
    return rendered, allowed


def verify_and_save(original: Image.Image, rendered: Image.Image, allowed: np.ndarray, output: Path) -> dict:
    a = np.array(original, dtype=np.uint8)
    b = np.array(rendered, dtype=np.uint8)
    if a.shape != b.shape:
        raise ValueError(f"shape mismatch: {output.name}")
    changed = np.any(a != b, axis=2)
    outside = changed & ~allowed
    clipped_outside = int(outside.sum())
    if clipped_outside:
        # Absolute final gate: regardless of antialiasing/stroke/inpaint behavior,
        # non-text pixels are restored byte-for-byte from the authoritative source.
        b[outside] = a[outside]
        rendered = Image.fromarray(b, "RGBA")
        changed = np.any(a != b, axis=2)
        outside = changed & ~allowed
    outside_count = int(outside.sum())
    if outside_count:
        raise ValueError(f"outside text region changed after restore: {output.name}: {outside_count}")
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered.save(output)
    return {
        "png": output.name,
        "changed_pixels": int(changed.sum()),
        "clipped_outside_pixels": clipped_outside,
        "outside_approved_text_region_changed_pixels": outside_count,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }


def load_specs() -> tuple[dict[str, dict], dict[str, dict]]:
    p = PROJECT / "assets/image_extraction/GADAT032/japanese_images/render_report.json"
    report = json.loads(p.read_text(encoding="utf-8"))
    by_png = {x["original_png"]: x for x in report.get("images", []) if x.get("original_png")}
    full = json.loads((PROJECT / "assets/full_extraction/GADAT032/manifest.json").read_text(encoding="utf-8"))
    resources = {f"block_{int(r['offset']):08x}.png": r for r in full["resources"] if r.get("images")}
    return by_png, resources


# Regions that need independent replacements inside a compound image.
MULTI: dict[str, list[tuple[tuple[int,int,int,int], str]]] = {
    # Preserve HP/EN/numbers exactly; replace Japanese suffix/labels only.
    "block_002dd000.png": [((145,32,205,78),"이상"),((286,32,430,78),"기력 최대"),((145,92,205,138),"미만"),((330,92,430,138),"이하"),((70,144,205,190),"전투 불능")],
    "block_002e2800.png": [
        ((16,18,88,38),"대기"),((16,36,88,56),"이동"),((16,54,88,74),"공격"),((16,72,88,92),"필살기"),
        ((16,90,88,110),"호위"),((16,108,88,129),"보급"),((16,126,88,146),"수리"),((16,144,88,164),"행동설정"),((16,162,88,182),"정보")],
    "block_002f0800.png": [
        ((14,18,86,38),"대기"),((14,36,86,56),"이동"),((14,54,86,74),"공격"),((14,72,86,92),"필살기"),
        ((14,90,86,110),"호위"),((14,108,86,129),"보급"),((14,126,86,146),"수리"),((14,144,86,164),"행동설정"),((14,162,86,182),"정보")],
    "block_002f8000.png": [
        ((5,4,75,24),"대기"),((5,22,75,42),"이동"),((5,40,75,60),"공격"),((5,58,75,78),"필살기"),
        ((5,76,75,96),"호위"),((5,94,75,114),"보급"),((5,112,75,132),"행동설정"),((5,130,75,151),"정보")],
    "block_002ea800.png": [((298,31,432,59),"선택 유닛만 표시"),((304,76,425,103),"모두 표시"),((298,119,432,147),"모두 숨김")],
    "block_002f3800.png": [((524,8,638,45),"샤프 슈터"),((485,78,530,110),"탐색"),((530,78,580,110),"반격"),((580,78,638,110),"공격")],
    "block_00c87800.png": [((72,1,164,34),"밀피유"),((23,132,92,166),"호감도")],
    "block_00c8e800.png": [((3,1,78,39),"호감도"),((88,123,185,166),"란파")],
    "block_00c95000.png": [((88,3,148,40),"민트"),((20,127,90,164),"호감도")],
    "block_00c9c000.png": [((52,1,138,44),"호감도"),((72,123,160,166),"포르테")],
    "block_00ca2800.png": [((78,4,143,33),"바닐라"),((38,134,103,164),"호감도")],
    "block_00ca9800.png": [((24,2,104,39),"호감도"),((69,123,150,158),"치토세")],
    "block_00e03000.png": [((160,14,235,42),"클리어 일시"),((338,14,410,42),"총 격추 수"),((458,14,520,42),"총점")],
}

SIMPLE_BOX = {
    "block_0034f800.png": (0,6,112,35),
    "block_00387000.png": (164,337,288,374),
    "block_00749000.png": (15,5,62,31), "block_0074a800.png": (15,5,62,31),
    "block_00a49000.png": (548,289,625,318),
    "block_00ad5800.png": (32,4,110,32), "block_00cf6000.png": (28,5,88,28),
    "block_00d2d000.png": (25,4,88,34), "block_00d2e000.png": (25,4,88,34),
    "block_00dee000.png": (40,5,100,30), "block_00df0000.png": (40,5,100,30),
    "block_00df2800.png": (35,5,105,32), "block_00df3800.png": (35,5,105,32),
}

G030_REGIONS = {
    "gjbk200i.png": [((20,10,220,40),"엘시오르 A블록")],
    "gjbk201i.png": [((20,10,220,40),"엘시오르 B블록")],
    "gjbk202i.png": [((20,10,220,40),"엘시오르 C블록")],
    "gjbk203i.png": [((20,10,220,40),"엘시오르 D블록")],
    "gjbk510i.png": [((370,200,500,240),"샤프 슈터"),((475,360,625,410),"샤프 슈터"),((468,430,522,478),"탐색"),((515,430,570,478),"반격"),((562,430,632,478),"공격")],
    "gjbk511i.png": [((5,80,330,120),"이동 지점을 선택해 주세요"),((85,108,195,138),"중계점 지정"),((270,200,410,245),"샤프 슈터"),((475,360,625,410),"샤프 슈터"),((468,430,522,478),"탐색"),((515,430,570,478),"반격"),((562,430,632,478),"공격")],
    "gjbk996i.png": [((370,200,500,240),"샤프 슈터"),((485,360,610,405),"하베스터"),((475,438,520,475),"탐색"),((520,438,565,475),"반격"),((565,438,625,475),"공격")],
    "gjbk997i.png": [((465,355,625,405),"샤프 슈터"),((470,430,520,475),"탐색"),((520,430,570,475),"반격"),((570,430,630,475),"공격")],
}


def render_regions(original: Image.Image, regions: list[tuple[tuple[int,int,int,int],str]], *, saturated: bool = False, font_path: Path = FONT_UI, max_size: int = 20, stroke: int | None = 0, glow: bool = False, flat_bright: bool = False, target_glyph_bbox: bool = False, dilation: int = 1) -> tuple[Image.Image, np.ndarray]:
    current = original.copy()
    allowed = np.zeros((original.height, original.width), bool)
    for box, text in regions:
        # Always measure style from the immutable Japanese original, never from an earlier edit.
        mask = source_mask(original, box, saturated=saturated)
        cleaned, _ = clean_masked(current, mask, dilation=dilation, clip_box=box)
        target = glyph_bbox(mask, box) if target_glyph_bbox else box
        current, _ = draw_styled(cleaned, text, target, original, mask, font_path=font_path, max_size=max_size, min_size=6, stroke=stroke, glow=glow, flat_bright=flat_bright)
        l,t,r,b = box; allowed[max(0,t):min(original.height,b),max(0,l):min(original.width,r)] = True
    return current, allowed


def render_score_name(original: Image.Image, text: str) -> tuple[Image.Image, np.ndarray]:
    mask = score_name_mask(original)
    box = glyph_bbox(mask, (105,8,270,45))
    cleaned, _ = clean_masked(original, mask, dilation=1, clip_box=(88,0,278,50))
    rendered, _ = draw_styled(
        cleaned,
        text,
        box,
        original,
        mask,
        font_path=FONT_TITLE,
        max_size=27,
        min_size=9,
        stroke=0,
        glow=True,
        flat_bright=False,
    )
    allowed = np.zeros((original.height, original.width), bool)
    allowed[0:min(50,original.height),88:min(278,original.width)] = True
    return rendered, allowed


def battle_result_regions(name: str) -> list[tuple[tuple[int,int,int,int],str]]:
    if name == "block_01207800.png": header_y=35; rows=[76,110,144,178,212,246,280,313]; total_y=360
    else: header_y=51; rows=[87,121,155,189,223,257,291,324]; total_y=366
    ships=["엘시오르","럭키 스타","쿵푸 파이터","트릭 마스터","해피 트리거","하베스터","샤프 슈터","기타"]
    out=[((20,10,140,47),"전투 결과"),((155,header_y,235,header_y+30),"격추 수"),((230,header_y,305,header_y+30),"전투 평가"),((300,header_y,375,header_y+30),"보너스"),((385,header_y,430,header_y+30),"득점"),((440,header_y,525,header_y+30),"누적 격추 수"),((520,header_y,605,header_y+30),"누적 점수")]
    out += [((15,y,165,y+28),txt) for y,txt in zip(rows,ships)]
    out.append(((15,total_y,80,total_y+35),"합계"))
    return out


def manual_authority() -> set[tuple[str,str]]:
    if not MANUAL_AUTHORITY.is_file():
        return set()
    payload=json.loads(MANUAL_AUTHORITY.read_text(encoding="utf-8"))
    return {
        (str(container), str(png))
        for container, data in payload.get("containers", {}).items()
        for png in data.get("images", [])
    }


def rework_targets() -> set[tuple[str,str]]:
    index=PROJECT/"analysis/strict_quality_review/index.json"
    payload=json.loads(index.read_text(encoding="utf-8"))
    targets={(x["container"],x["png"]) for sheet in payload["sheets"] for x in sheet["items"]}
    targets -= manual_authority()
    filtered: set[tuple[str,str]] = set()
    for container, png in targets:
        translated = PROJECT / f"assets/image_extraction/{container}/japanese_images/translated_png/{png}"
        if translated.is_file():
            continue
        filtered.add((container, png))
    return filtered


def rework_gadat030(targets: set[tuple[str,str]], output_root: Path | None = None) -> list[dict]:
    base=PROJECT/"assets/image_extraction/GADAT030/japanese_images"
    src=base/"png"; out=(output_root/"GADAT030" if output_root is not None else base/"translated_png")
    qa=[]
    for path in sorted(src.glob("*.png")):
        if ("GADAT030",path.name) not in targets or path.name not in G030_REGIONS:
            continue
        original=rgba(path)
        max_size=19 if path.name.startswith("gjbk20") else 17
        rendered,allowed=render_regions(
            original,
            G030_REGIONS[path.name],
            saturated=False,
            font_path=FONT_UI,
            max_size=max_size,
            stroke=1 if path.name == "gjbk201i.png" else 0,
            flat_bright=True,
            target_glyph_bbox=path.name in {"gjbk201i.png", "gjbk511i.png"},
        )
        item=verify_and_save(original,rendered,allowed,out/path.name); item["container"]="GADAT030"; qa.append(item)
    return qa


def rework_gadat032(targets: set[tuple[str,str]], output_root: Path | None = None) -> list[dict]:
    base=PROJECT/"assets/image_extraction/GADAT032/japanese_images"
    src=base/"png"; out=(output_root/"GADAT032" if output_root is not None else base/"translated_png")
    specs,resources=load_specs(); qa=[]; protected=manual_authority()
    existing_translated = base/"translated_png"
    for path in sorted(src.glob("*.png")):
        target=out/path.name
        if ("GADAT032",path.name) not in targets or ("GADAT032",path.name) in protected:
            continue
        if (existing_translated/path.name).is_file():
            continue
        spec=specs.get(path.name)
        if spec is None:
            raise KeyError(f"no translation spec for {path.name}")
        original=rgba(path); name=str(spec.get("resource_name") or ""); ko=str(spec.get("ko") or "")
        if path.name in MULTI:
            if path.name in {"block_002e2800.png", "block_002f0800.png", "block_002f8000.png"}:
                rendered,allowed=render_regions(original,MULTI[path.name],saturated=False,font_path=FONT_UI,max_size=17,stroke=0,flat_bright=True,target_glyph_bbox=True,dilation=1)
            elif path.name in {"block_002ea800.png", "block_002f3800.png"}:
                rendered,allowed=render_regions(original,MULTI[path.name],saturated=True,font_path=FONT_UI,max_size=17,stroke=0,flat_bright=True,target_glyph_bbox=True,dilation=2)
            elif path.name.startswith("block_002"):
                rendered,allowed=render_regions(original,MULTI[path.name],saturated=False,font_path=FONT_UI,max_size=17,stroke=0,flat_bright=True)
            elif path.name.startswith("block_00c"):
                rendered,allowed=render_regions(original,MULTI[path.name],saturated=True,font_path=FONT_UI,max_size=18,stroke=0,flat_bright=True,target_glyph_bbox=True,dilation=2)
            else:
                rendered,allowed=render_regions(original,MULTI[path.name],saturated=False,font_path=FONT_UI,max_size=18,stroke=0,flat_bright=True)
        elif path.name in {"block_01207800.png","block_0121a000.png"}:
            rendered,allowed=render_regions(original,battle_result_regions(path.name),saturated=False,font_path=FONT_UI,max_size=18,stroke=0,flat_bright=True)
        elif name.startswith("gybtn0") and name[5:7] in {"01","02","03","04","05","06"}:
            rendered,allowed=render_score_name(original,ko)
        elif name.startswith("gybtn1") and name[5:7] in {"11","12","13","14","15","16"}:
            rendered,allowed=replace_region_expanded(original,"스코어 표시",(0,5,min(96,original.width),29),(1,6,min(102,original.width-1),28),saturated=False,font_path=FONT_TITLE,max_size=19,min_size=7,stroke=1,glow=True,flat_bright=True)
        elif name.startswith("gebtn"):
            rendered,allowed=replace_region_expanded(original,ko,(35,5,min(120,original.width),32),(18,7,original.width-18,30),saturated=False,font_path=FONT_UI,max_size=18,min_size=7,stroke=1,glow=True,flat_bright=True)
        elif name.startswith("gmplc_pop"):
            h,w=original.height,original.width
            rendered,allowed=replace_region_expanded(original,ko,(8,max(0,h-31),w-8,h-2),(8,max(0,h-29),w-8,h-2),saturated=False,font_path=FONT_UI,max_size=18,min_size=7,stroke=1,glow=False,flat_bright=True)
        elif name.startswith("gproute"):
            rendered,allowed=render_text_only(original,ko,font_path=FONT_UI,glow=False,flat_bright=True)
        elif path.name in SIMPLE_BOX:
            box=SIMPLE_BOX[path.name]
            rendered,allowed=replace_region_expanded(original,ko,box,box,saturated=False,font_path=FONT_UI,max_size=19,min_size=7,stroke=1 if path.name not in {"block_00387000.png"} else 0,glow=path.name in {"block_0074a800.png","block_00dee000.png","block_00df0000.png","block_00df2800.png","block_00df3800.png"},flat_bright=True)
        elif spec.get("mode") == "text":
            rendered,allowed=render_text_only(original,ko,font_path=FONT_TITLE,glow=True,flat_bright=False)
        else:
            box=tuple(spec["box"]) if spec.get("box") else None
            if box is None:
                mask=source_mask(original,None,saturated=True)
                box=glyph_bbox(mask,(0,0,original.width,original.height))
            rendered,allowed=replace_region(original,ko,box,saturated=True,font_path=FONT_UI,max_size=max(20,int(spec.get("max_size") or 20)+8),min_size=max(6,int(spec.get("min_size") or 6)))
        item=verify_and_save(original,rendered,allowed,target); item.update({"container":"GADAT032","resource_name":name,"translation":ko}); qa.append(item)
    return qa


def main() -> None:
    targets=rework_targets()
    qa=rework_gadat030(targets)+rework_gadat032(targets)
    out=PROJECT/"build/image_compare/strict_rework_report.json"; out.parent.mkdir(parents=True,exist_ok=True)
    payload={"schema":"moonlit-strict-image-rework/v1","policy":STRICT_POLICY,"generated":len(qa),"items":qa}
    out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"generated":len(qa),"GADAT030":sum(x['container']=='GADAT030' for x in qa),"GADAT032":sum(x['container']=='GADAT032' for x in qa),"outside_changed":sum(x['outside_approved_text_region_changed_pixels'] for x in qa),"report":str(out)},ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
