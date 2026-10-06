#!/usr/bin/env python3
"""Patch Moonlit Lovers save/load chapter-title lookup tables.

The save/load detail pane does not render its first title from ``gktitle*.tex``.
It reads ``[LOG_CHAPTER]`` from GADAT000 ``adv.tbl``/``adv16.tbl`` and from
three mirrored ADV runtime copies.  This is the same class of issue that the
first Galaxy Angel patch had in its save/load title table: translating the
scenario SaveLabel and the visible chapter-title texture alone is insufficient.

This tool patches the canonical tables, their central IDX.DAT rows, and every
matching ADV FSTS runtime copy.  It also patches ``[LOG_SLG]`` in the same
resources so battle-stage titles cannot fall back to Japanese in the same UI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mmap
import shutil
import struct
from pathlib import Path

import galaxy_angel_build as builder
import galaxy_angel_translation as translation
import moonlit_lovers_resources as resources
from moonlit_lovers_speakers import (
    encode_lz,
    fsts_slot_end,
    next_pidx_offset,
    patch_central_idx_single,
    write_stream_without_gap_damage,
)


CONFIG_HALF_SPACE = b"\xa0"
CONFIG_SPACE_MARKER = "\ue000"
TARGET_PATHS = (
    "dat/gadat000/adv.tbl",
    "dat/gadat000/adv16.tbl",
)
EXPECTED_CHAPTER_ROWS = 16
EXPECTED_SLG_ROWS = 48
# Movie names shown after "ムービー：" in the backlog.
EXPECTED_MOVIE_ROWS = 25
EXPECTED_ADV_RUNTIME_COPIES = 3


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode_config_text(text: str, custom_map: dict[str, bytes]) -> bytes:
    output = bytearray()
    for char in text:
        if char == CONFIG_SPACE_MARKER:
            output.extend(CONFIG_HALF_SPACE)
        else:
            output.extend(translation.encode_text(char, custom_map))
    return bytes(output)


def split_ending(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    if line.endswith("\r"):
        return line[:-1], "\r"
    return line, ""


def load_titles(path: Path) -> dict[str, dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "moonlit-lovers-saveload-runtime-titles/v1":
        raise SystemExit(f"unsupported save/load title schema: {path}")
    chapter = {str(k): str(v) for k, v in payload.get("chapter", {}).items()}
    slg = {str(k): str(v) for k, v in payload.get("slg", {}).items()}
    if len(chapter) != EXPECTED_CHAPTER_ROWS:
        raise SystemExit(
            f"chapter translation count mismatch: {len(chapter)} != {EXPECTED_CHAPTER_ROWS}"
        )
    if not slg:
        raise SystemExit("SLG title translation table is empty")
    movie = {str(k): str(v) for k, v in payload.get("movie", {}).items()}
    if not movie:
        raise SystemExit("movie title translation table is empty")
    return {"LOG_CHAPTER": chapter, "LOG_SLG": slg, "LOG_MOVIE": movie}


def rebuild_log_tables(
    raw: bytes,
    title_maps: dict[str, dict[str, str]],
    custom_map: dict[str, bytes],
) -> tuple[bytes, dict[str, object]]:
    text = raw.decode("cp932")
    section = ""
    output: list[str] = []
    seen_rows = {"LOG_CHAPTER": 0, "LOG_SLG": 0, "LOG_MOVIE": 0}
    replaced_rows = {"LOG_CHAPTER": 0, "LOG_SLG": 0, "LOG_MOVIE": 0}
    replaced_values: dict[str, dict[str, str]] = {}

    for line in text.splitlines(keepends=True):
        body, ending = split_ending(line)
        stripped = body.strip()
        if stripped.startswith("[") and "]" in stripped:
            section = stripped[1 : stripped.index("]")]
            output.append(line)
            continue
        if section not in title_maps or not stripped.startswith("#") or "=" not in body:
            output.append(line)
            continue

        prefix, value = body.split("=", 1)
        value = value.rstrip(" \t")
        seen_rows[section] += 1
        translated = title_maps[section].get(value)
        if translated is None:
            output.append(line)
            continue
        safe = translated.replace(" ", CONFIG_SPACE_MARKER)
        output.append(prefix + "=" + safe + ending)
        replaced_rows[section] += 1
        replaced_values.setdefault(section, {})[value] = translated

    if seen_rows["LOG_CHAPTER"] != EXPECTED_CHAPTER_ROWS:
        raise SystemExit(
            f"LOG_CHAPTER row count mismatch: {seen_rows['LOG_CHAPTER']} != {EXPECTED_CHAPTER_ROWS}"
        )
    if replaced_rows["LOG_CHAPTER"] != EXPECTED_CHAPTER_ROWS:
        missing = sorted(set(title_maps["LOG_CHAPTER"]) - set(replaced_values.get("LOG_CHAPTER", {})))
        raise SystemExit(
            f"LOG_CHAPTER translation mismatch: {replaced_rows['LOG_CHAPTER']}/"
            f"{EXPECTED_CHAPTER_ROWS}; missing={missing}"
        )
    if seen_rows["LOG_SLG"] != EXPECTED_SLG_ROWS:
        raise SystemExit(
            f"LOG_SLG row count mismatch: {seen_rows['LOG_SLG']} != {EXPECTED_SLG_ROWS}"
        )
    if replaced_rows["LOG_SLG"] != EXPECTED_SLG_ROWS:
        raise SystemExit(
            f"LOG_SLG translation mismatch: {replaced_rows['LOG_SLG']}/"
            f"{EXPECTED_SLG_ROWS}"
        )
    if seen_rows["LOG_MOVIE"] != EXPECTED_MOVIE_ROWS:
        raise SystemExit(
            f"LOG_MOVIE row count mismatch: {seen_rows['LOG_MOVIE']} != {EXPECTED_MOVIE_ROWS}"
        )
    if replaced_rows["LOG_MOVIE"] != EXPECTED_MOVIE_ROWS:
        missing = sorted(set(title_maps["LOG_MOVIE"]) - set(replaced_values.get("LOG_MOVIE", {})))
        raise SystemExit(
            f"LOG_MOVIE translation mismatch: {replaced_rows['LOG_MOVIE']}/"
            f"{EXPECTED_MOVIE_ROWS}; missing={missing}"
        )

    rebuilt = encode_config_text("".join(output), custom_map)
    if len(rebuilt) > len(raw):
        raise SystemExit(f"ADV log table raw overflow: {len(rebuilt)} > {len(raw)}")
    rebuilt += b" " * (len(raw) - len(rebuilt))
    return rebuilt, {
        "seen_rows": seen_rows,
        "replaced_rows": replaced_rows,
        "replaced_values": replaced_values,
    }


def resource_by_path(
    container: bytes | bytearray,
    stem: str,
    path: str,
) -> resources.Resource:
    matches = [item for item in resources.container_resources(container, stem) if item.path == path]
    if len(matches) != 1:
        raise SystemExit(f"{stem} {path}: expected exactly one resource, got {len(matches)}")
    return matches[0]


def patch_gadat000_path(
    image: mmap.mmap,
    files: dict[str, builder.IsoFile],
    path: str,
    title_maps: dict[str, dict[str, str]],
    custom_map: dict[str, bytes],
) -> dict[str, object]:
    item = builder.resolve_iso_file(files, "GADAT000")
    begin = item.extent * builder.SECTOR
    container = bytearray(image[begin : begin + item.size])
    resource = resource_by_path(container, "GADAT000", path)
    before_raw = resources.decompress_resource(
        container, resource.offset, resource.raw_size, resource.compressed_size
    )
    patched_raw, detail = rebuild_log_tables(before_raw, title_maps, custom_map)
    encoded = encode_lz(patched_raw)
    record_map = resources.pidx_record_map(container, "GADAT000")
    slot_end = next_pidx_offset(record_map, resource.offset, len(container))
    write_stream_without_gap_damage(
        container,
        resource.offset,
        resource.compressed_size,
        encoded,
        slot_end,
        f"GADAT000 {path}",
    )
    if len(resource.record_positions) != 1:
        raise SystemExit(
            f"GADAT000 {path}: expected one PIDX record, got {resource.record_positions}"
        )
    record = resource.record_positions[0]
    struct.pack_into(
        "<III", container, record,
        resource.offset, len(patched_raw), len(encoded),
    )
    image[begin : begin + item.size] = container

    new_tuple = (resource.offset, len(patched_raw), len(encoded))
    file_id, idx_patched, idx_before = patch_central_idx_single(
        image, files, record_map, record, new_tuple
    )
    return {
        "path": path,
        "offset": resource.offset,
        "record": record,
        "raw_size": len(patched_raw),
        "raw_sha256_before": sha256(before_raw),
        "raw_sha256_after": sha256(patched_raw),
        "compressed_size_before": resource.compressed_size,
        "compressed_size_after": len(encoded),
        "slot_capacity": slot_end - resource.offset,
        "idx_file_id": file_id,
        "idx_tuple_before": list(idx_before),
        "idx_tuple_after": list(new_tuple),
        "idx_records_patched": idx_patched,
        **detail,
    }


def marker_bytes(title_maps: dict[str, dict[str, str]], custom_map: dict[str, bytes]) -> tuple[bytes, bytes]:
    japanese = "司令官はタクト".encode("cp932")
    korean = encode_config_text(
        title_maps["LOG_CHAPTER"]["司令官はタクト"].replace(" ", CONFIG_SPACE_MARKER),
        custom_map,
    )
    return japanese, korean


def patch_adv_runtime(
    image: mmap.mmap,
    files: dict[str, builder.IsoFile],
    title_maps: dict[str, dict[str, str]],
    custom_map: dict[str, bytes],
) -> list[dict[str, object]]:
    item = builder.resolve_iso_file(files, "ADV")
    begin = item.extent * builder.SECTOR
    container = bytearray(image[begin : begin + item.size])
    all_resources = resources.container_resources(container, "ADV")
    jp_marker, ko_marker = marker_bytes(title_maps, custom_map)
    rows: list[dict[str, object]] = []
    already = 0

    for resource in all_resources:
        try:
            raw = resources.decompress_resource(
                container, resource.offset, resource.raw_size, resource.compressed_size
            )
        except ValueError:
            continue
        if b"[LOG_CHAPTER]" not in raw:
            continue
        if jp_marker not in raw:
            if ko_marker in raw:
                already += 1
            continue

        patched_raw, detail = rebuild_log_tables(raw, title_maps, custom_map)
        encoded = encode_lz(patched_raw)
        slot_end = fsts_slot_end(resource, all_resources, len(container))
        write_stream_without_gap_damage(
            container,
            resource.offset,
            resource.compressed_size,
            encoded,
            slot_end,
            f"ADV save/load title runtime copy {resource.offset:#x}",
        )
        for record, base in zip(resource.record_positions, resource.fsts_bases):
            struct.pack_into(
                "<III", container, record + 4,
                resource.offset - base, len(patched_raw), len(encoded),
            )
        rows.append(
            {
                "offset": resource.offset,
                "record_positions": resource.record_positions,
                "fsts_bases": resource.fsts_bases,
                "raw_sha256_before": sha256(raw),
                "raw_sha256_after": sha256(patched_raw),
                "compressed_size_before": resource.compressed_size,
                "compressed_size_after": len(encoded),
                "slot_capacity": slot_end - resource.offset,
                **detail,
            }
        )

    if len(rows) + already != EXPECTED_ADV_RUNTIME_COPIES:
        raise SystemExit(
            "ADV save/load title runtime-copy count mismatch: "
            f"patched={len(rows)} already={already} expected={EXPECTED_ADV_RUNTIME_COPIES}"
        )
    image[begin : begin + item.size] = container
    return rows


def verify(
    image: mmap.mmap,
    files: dict[str, builder.IsoFile],
    title_maps: dict[str, dict[str, str]],
    custom_map: dict[str, bytes],
) -> dict[str, object]:
    jp_marker, ko_marker = marker_bytes(title_maps, custom_map)
    canonical_rows = []
    gadat_item = builder.resolve_iso_file(files, "GADAT000")
    gadat_begin = gadat_item.extent * builder.SECTOR
    gadat = bytes(image[gadat_begin : gadat_begin + gadat_item.size])
    for path in TARGET_PATHS:
        resource = resource_by_path(gadat, "GADAT000", path)
        raw = resources.decompress_resource(
            gadat, resource.offset, resource.raw_size, resource.compressed_size
        )
        if jp_marker in raw or ko_marker not in raw:
            raise SystemExit(f"GADAT000 save/load title verification failed: {path}")
        canonical_rows.append(
            {
                "path": path,
                "offset": resource.offset,
                "raw_sha256": sha256(raw),
            }
        )

    adv_item = builder.resolve_iso_file(files, "ADV")
    adv_begin = adv_item.extent * builder.SECTOR
    adv = bytes(image[adv_begin : adv_begin + adv_item.size])
    runtime_rows = []
    japanese_runtime = []
    for resource in resources.container_resources(adv, "ADV"):
        try:
            raw = resources.decompress_resource(
                adv, resource.offset, resource.raw_size, resource.compressed_size
            )
        except ValueError:
            continue
        if b"[LOG_CHAPTER]" not in raw:
            continue
        if jp_marker in raw:
            japanese_runtime.append(resource.offset)
        if ko_marker in raw:
            runtime_rows.append(
                {
                    "offset": resource.offset,
                    "raw_sha256": sha256(raw),
                }
            )
    if japanese_runtime:
        raise SystemExit(
            "Japanese LOG_CHAPTER runtime copies remain: "
            + ", ".join(f"{value:#x}" for value in japanese_runtime)
        )
    if len(runtime_rows) != EXPECTED_ADV_RUNTIME_COPIES:
        raise SystemExit(
            f"verified ADV save/load title copies: {len(runtime_rows)} != "
            f"{EXPECTED_ADV_RUNTIME_COPIES}"
        )
    return {
        "canonical": canonical_rows,
        "runtime_copies": runtime_rows,
        "canonical_verified": len(canonical_rows),
        "runtime_verified": len(runtime_rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iso", type=Path, required=True, help="ISO to patch or copy")
    parser.add_argument("--output-iso", type=Path, help="copy then patch; omit to patch in place")
    parser.add_argument("--titles", type=Path, required=True)
    parser.add_argument("--encoding-map", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify an already-patched ISO without modifying it.",
    )
    args = parser.parse_args()

    title_maps = load_titles(args.titles)
    custom_map = translation.load_custom_map(args.encoding_map) or {}
    output = args.output_iso or args.iso
    if args.verify_only and args.output_iso:
        raise SystemExit("--verify-only cannot be combined with --output-iso")
    if args.output_iso:
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.iso, output)

    if args.verify_only:
        canonical: list[dict[str, object]] = []
        runtime: list[dict[str, object]] = []
        with output.open("rb") as stream, mmap.mmap(
            stream.fileno(), 0, access=mmap.ACCESS_READ
        ) as image:
            files = builder.iso_files(image)
            verification = verify(image, files, title_maps, custom_map)
    else:
        with output.open("r+b") as stream, mmap.mmap(
            stream.fileno(), 0, access=mmap.ACCESS_WRITE
        ) as image:
            files = builder.iso_files(image)
            canonical = [
                patch_gadat000_path(image, files, path, title_maps, custom_map)
                for path in TARGET_PATHS
            ]
            runtime = patch_adv_runtime(image, files, title_maps, custom_map)
            image.flush()
            verification = verify(image, files, title_maps, custom_map)

    payload = {
        "schema": "moonlit-lovers-saveload-runtime-title-patch/v1",
        "input_iso": str(args.iso),
        "output_iso": str(output),
        "title_asset": str(args.titles),
        "canonical": canonical,
        "runtime_patched": runtime,
        "verification": verification,
        "verify_only": args.verify_only,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"patched save/load runtime titles: canonical={len(canonical)} "
        f"ADV={len(runtime)}; verified={verification['canonical_verified']}+"
        f"{verification['runtime_verified']} output={output}"
    )


if __name__ == "__main__":
    main()
