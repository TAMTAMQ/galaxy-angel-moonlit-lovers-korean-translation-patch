#!/usr/bin/env python3
"""Build and inspect Galaxy Angel: Moonlit Lovers' embedded 24x24 font.

Moonlit Lovers uses the same 7,045-glyph compact Shift-JIS mapping and paired
24x24 PSMT4 storage proven for Eternal Lovers: two independent 2bpp glyph
planes share each 288-byte cell.  The table location differs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mmap
import shutil
from pathlib import Path

from PIL import Image

import eternal_lovers_font as base
import galaxy_angel_build as builder


FONT_VADDR = 0x002E4010
FONT_FILE_OFFSET = 0x001E5010
ORIGINAL_GLYPHS = 7045
FIRST_REPLACEMENT_INDEX = 5000
PAIR_BYTES = base.PAIR_BYTES
ORIGINAL_FONT_SHA256 = "b07fb061258acca0f826fc4fde18f98bbac1055bf739cfc48afcbdb1ef9b05c3"


def translation_entries(source: Path):
    if source.is_dir():
        index = json.loads((source / "index.json").read_text(encoding="utf-8"))
        for item in index.get("segments", []):
            segment = json.loads((source / item["path"]).read_text(encoding="utf-8"))
            yield from segment.get("units", [])
        selection = source / "selection_units.json"
        if selection.is_file():
            yield from json.loads(selection.read_text(encoding="utf-8")).get("units", [])
        mission_layout = source / "mission_layout_overrides.json"
        if mission_layout.is_file():
            for entry in json.loads(mission_layout.read_text(encoding="utf-8")).get("entries", []):
                yield {**entry, "use_translation": True}
        for path in sorted(source.glob("save_label_translations*.json")):
            for entry in json.loads(path.read_text(encoding="utf-8")).get("entries", []):
                yield {**entry, "use_translation": True}
        return
    payload = json.loads(source.read_text(encoding="utf-8"))
    yield from payload.get(
        "entries", payload.get("candidates", payload.get("units", []))
    )


def expand_hangul_glyph_horizontally(raw: bytes, scale: float) -> bytes:
    """Widen Hangul ink inside the fixed 24x24 cell without changing advance.

    The game advances every full-width glyph by the whole 24-pixel cell.  Pretendard
    rendered in the proven 20x20 inset usually occupies only 15-18 horizontal pixels,
    which makes Korean mission text look as though spaces were inserted between every
    syllable.  Expanding only the nonzero Hangul ink keeps the runtime metrics and line
    wrapping unchanged while reducing that optical gap.
    """
    if scale <= 1.0:
        return raw
    image = base.decode_glyph(raw)
    bbox = image.getbbox()
    if bbox is None:
        return raw
    left, top, right, bottom = bbox
    width = right - left
    target_width = min(base.GLYPH_WIDTH, max(width, int(round(width * scale))))
    if target_width == width:
        return raw
    crop = image.crop((left, 0, right, base.GLYPH_HEIGHT))
    widened = crop.resize((target_width, base.GLYPH_HEIGHT), Image.Resampling.LANCZOS)
    canvas = Image.new("L", (base.GLYPH_WIDTH, base.GLYPH_HEIGHT), 0)
    canvas.paste(widened, ((base.GLYPH_WIDTH - target_width) // 2, 0))
    levels = [(value * 3 + 127) // 255 for value in canvas.get_flattened_data()]
    return bytes(
        (levels[i] << 6) | (levels[i + 1] << 4)
        | (levels[i + 2] << 2) | levels[i + 3]
        for i in range(0, len(levels), 4)
    )


def collect_custom_chars(translations: list[Path]) -> list[str]:
    chars: set[str] = set()
    for source in translations:
        for entry in translation_entries(source):
            if not entry.get("use_translation") or not entry.get("translation"):
                continue
            for char in entry["translation"]:
                try:
                    char.encode("cp932")
                except UnicodeEncodeError:
                    chars.add(char)
    return sorted(chars)


def safe_indices() -> list[int]:
    return [
        index
        for index in range(ORIGINAL_GLYPHS - 1, FIRST_REPLACEMENT_INDEX - 1, -1)
        if base.is_script_safe_sjis(base.index_to_sjis(index))
    ]


def verify_source_table(data: bytes) -> None:
    table_size = ((ORIGINAL_GLYPHS + 1) // 2) * PAIR_BYTES
    table_end = FONT_FILE_OFFSET + table_size
    if table_end > len(data):
        raise SystemExit(
            f"embedded font exceeds ELF: {table_end:#x} > {len(data):#x}"
        )
    digest = hashlib.sha256(data[FONT_FILE_OFFSET:table_end]).hexdigest()
    if digest != ORIGINAL_FONT_SHA256:
        raise SystemExit(
            "Moonlit Lovers font source fingerprint mismatch: "
            f"{digest} != {ORIGINAL_FONT_SHA256}"
        )


def build_font(
    translations: list[Path],
    input_elf: Path,
    output_elf: Path,
    map_output: Path,
    font_path: Path,
    font_size: int,
    font_index: int,
    hangul_horizontal_scale: float = 1.0,
) -> None:
    chars = collect_custom_chars(translations)
    available_indices = safe_indices()
    if len(chars) > len(available_indices):
        raise SystemExit(
            f"custom glyph capacity exceeded: {len(chars)} > {len(available_indices)}"
        )

    data = bytearray(input_elf.read_bytes())
    verify_source_table(data)
    mapping: dict[str, dict[str, int | str]] = {}
    for char, index in zip(chars, available_indices, strict=False):
        offset = FONT_FILE_OFFSET + (index // 2) * PAIR_BYTES
        block = bytearray(data[offset:offset + PAIR_BYTES])
        original_block = bytes(block)
        rendered = base.render_glyph(char, font_path, font_size, font_index)
        if "가" <= char <= "힣" and hangul_horizontal_scale > 1.0:
            rendered = expand_hangul_glyph_horizontally(rendered, hangul_horizontal_scale)
        base.merge_paired_glyph(block, index & 1, rendered)
        target_mask = 0xCC if index & 1 else 0x33
        if any((old ^ new) & ~target_mask for old, new in zip(original_block, block)):
            raise AssertionError(f"paired partner plane changed for glyph {index}")
        expected = list(base.decode_glyph(rendered).get_flattened_data())
        actual = list(base.decode_paired_glyph(block, index & 1).get_flattened_data())
        if actual != expected:
            raise AssertionError(f"paired glyph verification failed for glyph {index}")
        data[offset:offset + PAIR_BYTES] = block
        mapping[char] = {
            "hex": base.index_to_sjis(index).hex(),
            "glyph_index": index,
            "pair_file_offset": offset,
        }

    output_elf.parent.mkdir(parents=True, exist_ok=True)
    output_elf.write_bytes(data)
    map_output.parent.mkdir(parents=True, exist_ok=True)
    map_output.write_text(
        json.dumps(
            {
                "schema": "moonlit-lovers-font-map/v1",
                "font": str(font_path),
                "font_size": font_size,
                "font_index": font_index,
                "hangul_horizontal_scale": hangul_horizontal_scale,
                "font_file_offset": FONT_FILE_OFFSET,
                "font_vaddr": FONT_VADDR,
                "glyph_format": (
                    "paired 24x24 PSMT4; two 2bpp glyph planes per 288-byte cell"
                ),
                "glyph_bytes": base.GLYPH_BYTES,
                "pair_bytes": PAIR_BYTES,
                "replacement_index_floor": FIRST_REPLACEMENT_INDEX,
                "safe_capacity": len(available_indices),
                "characters": mapping,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"patched {len(mapping)} custom glyphs; "
        f"capacity={len(available_indices)} output={output_elf}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    extract = sub.add_parser("extract")
    extract.add_argument("--iso", type=Path, required=True)
    extract.add_argument("--output", type=Path, required=True)

    install = sub.add_parser("install")
    install.add_argument("--input-iso", type=Path, required=True)
    install.add_argument("--font-elf", type=Path, required=True)
    install.add_argument("--output-iso", type=Path, required=True)

    inspect = sub.add_parser("inspect")
    inspect.add_argument("--elf", type=Path, required=True)
    inspect.add_argument("--index", type=int, required=True)
    inspect.add_argument("--output", type=Path, required=True)
    inspect.add_argument("--variants", action="store_true")

    build = sub.add_parser("build")
    build.add_argument("--translations", type=Path, action="append", required=True)
    build.add_argument("--input-elf", type=Path, required=True)
    build.add_argument("--output-elf", type=Path, required=True)
    build.add_argument("--map-output", type=Path, required=True)
    build.add_argument(
        "--font",
        type=Path,
        default=Path(
            r"vendor\pretendard\packages\pretendard\dist\public\static\alternative"
            r"\Pretendard-Bold.ttf"
        ),
    )
    build.add_argument("--font-size", type=int, default=20)
    build.add_argument("--font-index", type=int, default=0)
    build.add_argument(
        "--hangul-horizontal-scale",
        type=float,
        default=1.0,
        help="Widen Hangul ink inside each fixed 24x24 glyph cell (e.g. 1.25).",
    )
    args = parser.parse_args()

    if args.command == "extract":
        with args.iso.open("rb") as stream, mmap.mmap(
            stream.fileno(), 0, access=mmap.ACCESS_READ
        ) as image:
            item = builder.iso_files(image)["SLPM_654.29"]
            begin = item.extent * builder.SECTOR
            data = bytes(image[begin:begin + item.size])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(data)
        print(
            f"extracted SLPM_654.29 size={len(data)} "
            f"sha256={hashlib.sha256(data).hexdigest()} output={args.output}"
        )
        return

    if args.command == "install":
        elf = args.font_elf.read_bytes()
        args.output_iso.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.input_iso, args.output_iso)
        with args.output_iso.open("r+b") as stream, mmap.mmap(
            stream.fileno(), 0, access=mmap.ACCESS_WRITE
        ) as image:
            item = builder.iso_files(image)["SLPM_654.29"]
            if len(elf) != item.size:
                raise SystemExit(f"ELF size mismatch: {len(elf)} != {item.size}")
            begin = item.extent * builder.SECTOR
            image[begin:begin + item.size] = elf
            image.flush()
        with args.output_iso.open("rb") as stream, mmap.mmap(
            stream.fileno(), 0, access=mmap.ACCESS_READ
        ) as image:
            item = builder.iso_files(image)["SLPM_654.29"]
            begin = item.extent * builder.SECTOR
            installed = bytes(image[begin:begin + item.size])
        if installed != elf:
            raise SystemExit("installed ELF readback mismatch")
        print(
            f"installed SLPM_654.29 sha256={hashlib.sha256(installed).hexdigest()} "
            f"output={args.output_iso}"
        )
        return

    if args.command == "inspect":
        data = args.elf.read_bytes()
        start = FONT_FILE_OFFSET + (args.index // 2) * PAIR_BYTES
        raw = data[start:start + PAIR_BYTES]
        image = (
            base.decode_variants(raw, args.index & 1)
            if args.variants
            else base.decode_paired_glyph(raw, args.index & 1)
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if not args.variants:
            image = image.resize((192, 192), Image.Resampling.NEAREST)
        image.save(args.output)
        print(
            f"index={args.index} sjis={base.index_to_sjis(args.index).hex()} "
            f"pair_file_offset={start:#x} "
            f"pair_vaddr={FONT_VADDR + (args.index // 2) * PAIR_BYTES:#x}"
        )
        return

    build_font(
        args.translations,
        args.input_elf,
        args.output_elf,
        args.map_output,
        args.font,
        args.font_size,
        args.font_index,
        args.hangul_horizontal_scale,
    )


if __name__ == "__main__":
    main()
