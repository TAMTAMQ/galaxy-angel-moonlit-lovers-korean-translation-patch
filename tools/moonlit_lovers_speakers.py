#!/usr/bin/env python3
"""Patch Moonlit Lovers' speaker-name table and its ADV runtime copies.

The ADV script renders ``\\Speaker(...)`` names by looking up ``speaker.tbl``;
those names are not part of the dialogue strings.  Moonlit Lovers stores the
canonical table once in GADAT000 and mirrors the same raw table in two ADV FSTS
banks.  This tool patches all three copies without relocating a resource and
updates both the local PIDX leaf and its flat IDX.DAT mirror for GADAT000.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mmap
import re
import shutil
import struct
from pathlib import Path

import galaxy_angel_build as builder
import galaxy_angel_translation as translation
import ikusa_lz
import moonlit_lovers_resources as resources


ENTRY_RE = re.compile(r"^(?P<prefix>[ \t]*#(?P<id>\d+)[ \t]*=[ \t]*)(?P<rest>.*)$")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode_lz(raw: bytes) -> bytes:
    normal = ikusa_lz.compress(raw)
    optimal = ikusa_lz.compress_optimal(raw)
    encoded = optimal if len(optimal) < len(normal) else normal
    decoded, used = ikusa_lz.decompress(encoded)
    if decoded != raw or used != len(encoded):
        raise SystemExit("speaker table compressor round-trip failed")
    return encoded


def split_ending(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    if line.endswith("\r"):
        return line[:-1], "\r"
    return line, ""


def split_comment(rest: str) -> tuple[str, str]:
    candidates = [pos for marker in (";", "//") if (pos := rest.find(marker)) >= 0]
    if not candidates:
        return rest, ""
    pos = min(candidates)
    start = pos
    while start > 0 and rest[start - 1] in " \t":
        start -= 1
    return rest[:start], rest[start:]


def rebuild_table(
    raw: bytes,
    names: dict[str, str],
    preserve_ids: set[str],
    custom_map: dict[str, bytes],
) -> tuple[bytes, dict[str, dict[str, str]]]:
    text = raw.decode("cp932")
    seen: set[str] = set()
    changes: dict[str, dict[str, str]] = {}
    output: list[str] = []

    for line in text.splitlines(keepends=True):
        body, ending = split_ending(line)
        match = ENTRY_RE.match(body)
        if not match:
            output.append(line)
            continue
        speaker_id = match.group("id")
        if speaker_id in preserve_ids:
            seen.add(speaker_id)
            output.append(line)
            continue
        target = names.get(speaker_id)
        if target is None:
            output.append(line)
            continue
        _value, suffix = split_comment(match.group("rest"))
        old_value = _value.rstrip(" \t")
        output.append(match.group("prefix") + target + suffix + ending)
        seen.add(speaker_id)
        changes[speaker_id] = {"before": old_value, "after": target}

    missing = sorted(set(names) - seen, key=lambda value: int(value))
    if missing:
        raise SystemExit("speaker IDs missing from table: " + ", ".join(missing))
    missing_preserved = sorted(preserve_ids - seen, key=lambda value: int(value))
    if missing_preserved:
        raise SystemExit("preserved speaker IDs missing from table: " + ", ".join(missing_preserved))

    rebuilt = translation.encode_text("".join(output), custom_map)
    if len(rebuilt) > len(raw):
        raise SystemExit(f"speaker table raw overflow: {len(rebuilt)} > {len(raw)}")
    rebuilt += b" " * (len(raw) - len(rebuilt))
    return rebuilt, changes


def resource_by_offset(container: bytes | bytearray, stem: str, offset: int) -> resources.Resource:
    matches = [item for item in resources.container_resources(container, stem) if item.offset == offset]
    if len(matches) != 1:
        raise SystemExit(f"{stem} resource {offset:#x}: expected 1 match, got {len(matches)}")
    return matches[0]


def next_pidx_offset(record_map: dict[int, tuple[int, int, int]], offset: int, size: int) -> int:
    return min((item for item in record_map if item > offset), default=size)


def fsts_slot_end(resource: resources.Resource, all_resources: list[resources.Resource], size: int) -> int:
    bases = set(resource.fsts_bases)
    if resource.source_kind != "fsts" or len(bases) != 1:
        raise SystemExit(f"ADV speaker copy is not a single-bank FSTS resource: {resource.offset:#x}")
    base = next(iter(bases))
    all_bases = sorted({item for row in all_resources for item in row.fsts_bases})
    bank_end = min((item for item in all_bases if item > base), default=size)
    following = [
        row.offset for row in all_resources
        if row.offset > resource.offset and set(row.fsts_bases) == {base}
    ]
    return min(following, default=bank_end)


def write_stream_without_gap_damage(
    container: bytearray,
    offset: int,
    old_size: int,
    encoded: bytes,
    slot_end: int,
    label: str,
) -> None:
    if offset + len(encoded) > slot_end:
        raise SystemExit(
            f"{label} compressed overflow: {len(encoded)} > {slot_end - offset}"
        )
    if len(encoded) > old_size:
        growth = container[offset + old_size:offset + len(encoded)]
        if any(growth):
            raise SystemExit(
                f"{label} needs {len(encoded) - old_size} growth bytes but the gap is not zero; "
                "refusing to overwrite adjacent runtime metadata"
            )
    container[offset:offset + len(encoded)] = encoded
    if len(encoded) < old_size:
        container[offset + len(encoded):offset + old_size] = bytes(old_size - len(encoded))


def patch_central_idx_single(
    image: mmap.mmap,
    files: dict[str, builder.IsoFile],
    record_map: dict[int, tuple[int, int, int]],
    target_record: int,
    new_tuple: tuple[int, int, int],
) -> tuple[int, int, tuple[int, int, int]]:
    """Patch one IDX.DAT tuple even when unrelated mirror rows are stale.

    Some late Moonlit builds have one unrelated GADAT000 PIDX row whose flat
    IDX mirror no longer matches byte-for-byte.  The generic builder helper
    intentionally rejects that whole container as incomplete, which also
    blocks a safe speaker.tbl update.  Here we still identify the dominant
    file id from all matching local tuples, then update only the unique flat
    row for the speaker resource's offset.  This keeps the same safety model
    without requiring every unrelated GADAT000 row to be synchronized first.
    """
    idx_file = builder.resolve_iso_file(files, "IDX")
    idx_begin = idx_file.extent * builder.SECTOR

    old_by_record = {
        record: (offset, raw_size, compressed_size)
        for offset, (record, raw_size, compressed_size) in record_map.items()
    }
    if target_record not in old_by_record:
        raise SystemExit(f"target PIDX record not found: {target_record:#x}")

    records_by_tuple: dict[tuple[int, int, int], list[int]] = {}
    for record, old_tuple in old_by_record.items():
        records_by_tuple.setdefault(old_tuple, []).append(record)

    candidates: dict[int, set[int]] = {}
    for relative in range(0, idx_file.size - 15, 4):
        file_id, offset, raw_size, compressed_size = struct.unpack_from(
            "<IIII", image, idx_begin + relative
        )
        if offset % builder.SECTOR or compressed_size < 8:
            continue
        for record in records_by_tuple.get((offset, raw_size, compressed_size), ()):
            candidates.setdefault(file_id, set()).add(record)

    if not candidates:
        raise SystemExit("IDX.DAT mirror for GADAT000 was not found")
    ranked = sorted(candidates.items(), key=lambda item: len(item[1]), reverse=True)
    file_id, matched_records = ranked[0]
    if len(ranked) > 1 and len(ranked[1][1]) == len(matched_records):
        raise SystemExit("IDX.DAT mirror file id is ambiguous")

    target_offset, old_raw_size, _old_compressed_size = old_by_record[target_record]
    hits: list[tuple[int, tuple[int, int, int]]] = []
    for relative in range(0, idx_file.size - 15, 4):
        row_file_id, offset, raw_size, compressed_size = struct.unpack_from(
            "<IIII", image, idx_begin + relative
        )
        if row_file_id != file_id or offset != target_offset:
            continue
        if raw_size != old_raw_size:
            continue
        hits.append((idx_begin + relative, (offset, raw_size, compressed_size)))
    if len(hits) != 1:
        raise SystemExit(
            f"IDX.DAT speaker row lookup failed for file id {file_id}, "
            f"offset {target_offset:#x}: expected 1 row, got {len(hits)}"
        )

    position, before_tuple = hits[0]
    patched = 0
    if before_tuple != new_tuple:
        struct.pack_into("<III", image, position + 4, *new_tuple)
        patched = 1
    return file_id, patched, before_tuple


def patch_gadat000(
    image: mmap.mmap,
    files: dict[str, builder.IsoFile],
    canonical: dict,
    patched_raw: bytes,
) -> dict:
    item = builder.resolve_iso_file(files, canonical["container"])
    begin = item.extent * builder.SECTOR
    container = bytearray(image[begin:begin + item.size])
    record_map = resources.pidx_record_map(container, "GADAT000")
    offset = int(canonical["offset"])
    resource = resource_by_offset(container, "GADAT000", offset)
    before_raw = resources.decompress_resource(
        container, resource.offset, resource.raw_size, resource.compressed_size
    )
    if len(patched_raw) != resource.raw_size:
        raise SystemExit(
            f"GADAT000 speaker raw size changed: {len(patched_raw)} != {resource.raw_size}"
        )
    encoded = encode_lz(patched_raw)
    slot_end = next_pidx_offset(record_map, offset, len(container))
    write_stream_without_gap_damage(
        container, offset, resource.compressed_size, encoded, slot_end, "GADAT000 speaker.tbl"
    )
    record = resource.record_positions[0]
    struct.pack_into("<III", container, record, offset, len(patched_raw), len(encoded))
    image[begin:begin + item.size] = container

    new_tuple = (offset, len(patched_raw), len(encoded))
    file_id, idx_patched, idx_tuple_before = patch_central_idx_single(
        image,
        files,
        record_map,
        record,
        new_tuple,
    )
    return {
        "container": "GADAT000",
        "offset": offset,
        "record": record,
        "raw_sha256_before": sha256(before_raw),
        "raw_sha256_after": sha256(patched_raw),
        "compressed_size_before": resource.compressed_size,
        "compressed_size_after": len(encoded),
        "slot_capacity": slot_end - offset,
        "idx_file_id": file_id,
        "idx_tuple_before": list(idx_tuple_before),
        "idx_tuple_after": list(new_tuple),
        "idx_records_patched": idx_patched,
    }


def patch_adv(
    image: mmap.mmap,
    files: dict[str, builder.IsoFile],
    runtime_copies: list[dict],
    patched_raw: bytes,
) -> list[dict]:
    item = builder.resolve_iso_file(files, "ADV")
    begin = item.extent * builder.SECTOR
    container = bytearray(image[begin:begin + item.size])
    all_resources = resources.container_resources(container, "ADV")
    rows = []
    for copy in runtime_copies:
        offset = int(copy["offset"])
        resource = resource_by_offset(container, "ADV", offset)
        before_raw = resources.decompress_resource(
            container, resource.offset, resource.raw_size, resource.compressed_size
        )
        if len(patched_raw) != resource.raw_size:
            raise SystemExit(
                f"ADV speaker copy {offset:#x} raw size changed: "
                f"{len(patched_raw)} != {resource.raw_size}"
            )
        encoded = encode_lz(patched_raw)
        slot_end = fsts_slot_end(resource, all_resources, len(container))
        write_stream_without_gap_damage(
            container,
            offset,
            resource.compressed_size,
            encoded,
            slot_end,
            f"ADV speaker copy {offset:#x}",
        )
        for record, base in zip(resource.record_positions, resource.fsts_bases):
            struct.pack_into(
                "<III", container, record + 4,
                offset - base, len(patched_raw), len(encoded),
            )
        rows.append(
            {
                "container": "ADV",
                "offset": offset,
                "record_positions": resource.record_positions,
                "fsts_bases": resource.fsts_bases,
                "raw_sha256_before": sha256(before_raw),
                "raw_sha256_after": sha256(patched_raw),
                "compressed_size_before": resource.compressed_size,
                "compressed_size_after": len(encoded),
                "slot_capacity": slot_end - offset,
            }
        )
    image[begin:begin + item.size] = container
    return rows


def verify_iso(
    image: mmap.mmap,
    files: dict[str, builder.IsoFile],
    canonical: dict,
    runtime_copies: list[dict],
    expected_raw: bytes,
) -> list[dict]:
    verified = []
    checks = [canonical, *runtime_copies]
    for check in checks:
        stem = check["container"]
        item = builder.resolve_iso_file(files, stem)
        begin = item.extent * builder.SECTOR
        container = bytes(image[begin:begin + item.size])
        resource = resource_by_offset(container, stem, int(check["offset"]))
        raw = resources.decompress_resource(
            container, resource.offset, resource.raw_size, resource.compressed_size
        )
        if raw != expected_raw:
            raise SystemExit(f"speaker readback mismatch: {stem} {resource.offset:#x}")
        verified.append(
            {
                "container": stem,
                "offset": resource.offset,
                "raw_size": resource.raw_size,
                "compressed_size": resource.compressed_size,
                "raw_sha256": sha256(raw),
            }
        )
    return verified


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iso", type=Path, required=True, help="ISO to patch or copy")
    parser.add_argument("--output-iso", type=Path, help="copy then patch; omit to patch --iso in place")
    parser.add_argument("--names", type=Path, required=True)
    parser.add_argument("--encoding-map", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    spec = json.loads(args.names.read_text(encoding="utf-8"))
    canonical = dict(spec["canonical"])
    runtime_copies = [dict(item) for item in spec["runtime_copies"]]
    names = {str(key): str(value) for key, value in spec["names"].items()}
    preserve_ids = {str(value) for value in spec.get("preserve_ids", [])}
    custom_map = translation.load_custom_map(args.encoding_map) or {}

    output = args.output_iso or args.iso
    if args.output_iso:
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.iso, output)

    with output.open("r+b") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_WRITE) as image:
        files = builder.iso_files(image)
        item = builder.resolve_iso_file(files, canonical["container"])
        begin = item.extent * builder.SECTOR
        source_container = bytes(image[begin:begin + item.size])
        source_resource = resource_by_offset(
            source_container, canonical["container"], int(canonical["offset"])
        )
        source_raw = resources.decompress_resource(
            source_container,
            source_resource.offset,
            source_resource.raw_size,
            source_resource.compressed_size,
        )
        pristine_hash = canonical.get("pristine_sha256")
        source_hash = sha256(source_raw)
        patched_raw, changes = rebuild_table(source_raw, names, preserve_ids, custom_map)
        gadat = patch_gadat000(image, files, canonical, patched_raw)
        adv = patch_adv(image, files, runtime_copies, patched_raw)
        image.flush()
        verified = verify_iso(image, files, canonical, runtime_copies, patched_raw)

    payload = {
        "schema": "moonlit-lovers-speaker-patch/v1",
        "input_iso": str(args.iso),
        "output_iso": str(output),
        "source_raw_sha256": source_hash,
        "source_matches_pristine": source_hash == pristine_hash if pristine_hash else None,
        "patched_raw_sha256": sha256(patched_raw),
        "speaker_names_patched": len(changes),
        "preserved_ids": sorted(preserve_ids, key=int),
        "changes": changes,
        "canonical": gadat,
        "runtime_copies": adv,
        "verified": verified,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"patched {len(changes)} speaker names + {len(adv)} ADV runtime copies; "
        f"readback={len(verified)}/{1 + len(adv)} output={output}"
    )


if __name__ == "__main__":
    main()
