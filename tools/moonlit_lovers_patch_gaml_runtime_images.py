#!/usr/bin/env python3
"""Patch GADAT032 image runtime copies cached as raw LZ streams in GAML.DAT.

Moonlit Lovers keeps a second, unindexed cache of system UI textures in
GAML.DAT.  The normal image build patched GADAT032 and ADV but did not scan
GAML, so the SELECT/pause menu could still load Japanese copies.

The Japanese ISO is used only to identify each original compressed GADAT032
stream and its exact GAML slot.  The already-built Korean stream is taken from
the target ISO's GADAT032 primary.  Slots stay fixed; only the stream and its
existing zero-alignment gap are overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mmap
from pathlib import Path

import galaxy_angel_build as builder
import ikusa_lz


MAX_ALIGNMENT_GAP = 0x800


def scan_lz_streams(data: bytes) -> dict[str, list[tuple[int, int, int]]]:
    """Index valid Ikusa-LZ streams by decompressed SHA-256.

    GAML sometimes stores the same TEX with a different compressed byte stream
    than GADAT032, so byte-identical searching alone is incomplete.
    """
    mapping: dict[str, list[tuple[int, int, int]]] = {}
    cursor = 0
    while True:
        hit = data.find(b" 3;1", cursor)
        if hit < 0:
            return mapping
        cursor = hit + 1
        try:
            raw, used = ikusa_lz.decompress(data, hit)
        except Exception:
            continue
        digest = hashlib.sha256(raw).hexdigest()
        mapping.setdefault(digest, []).append((hit, used, len(raw)))


def slot_capacity(data: bytes | bytearray | memoryview, hit: int, old_size: int) -> int:
    cursor = hit + old_size
    limit = min(len(data), cursor + MAX_ALIGNMENT_GAP)
    while cursor < limit and data[cursor] == 0:
        cursor += 1
    return cursor - hit


def validate_stream(blob: bytes, expected_raw_size: int, expected_used: int, label: str) -> bytes:
    raw, used = ikusa_lz.decompress(blob)
    if len(raw) != expected_raw_size or used != expected_used:
        raise SystemExit(
            f"{label}: LZ mismatch raw={len(raw)}/{expected_raw_size} "
            f"used={used}/{expected_used}"
        )
    return raw


def patch(
    original_iso: Path,
    iso_path: Path,
    image_report: Path,
    report_path: Path | None = None,
) -> dict:
    payload = json.loads(image_report.read_text(encoding="utf-8"))
    if str(payload.get("primary_container", "")).upper() != "GADAT032":
        raise SystemExit("image report must be for GADAT032")

    with original_iso.open("rb") as source_stream, mmap.mmap(
        source_stream.fileno(), 0, access=mmap.ACCESS_READ
    ) as source_image:
        source_files = builder.iso_files(source_image)
        source_gadat = builder.resolve_iso_file(source_files, "GADAT032")
        source_gaml = builder.resolve_iso_file(source_files, "GAML")
        source_gadat_begin = source_gadat.extent * builder.SECTOR
        source_gaml_begin = source_gaml.extent * builder.SECTOR
        source_gadat_data = bytes(
            source_image[source_gadat_begin : source_gadat_begin + source_gadat.size]
        )
        source_gaml_data = bytes(
            source_image[source_gaml_begin : source_gaml_begin + source_gaml.size]
        )
    source_gaml_streams = scan_lz_streams(source_gaml_data)

    entries: list[dict] = []
    patched_slots = 0
    already_patched_slots = 0
    changed_bytes = 0

    with iso_path.open("r+b") as target_stream, mmap.mmap(target_stream.fileno(), 0) as image:
        target_files = builder.iso_files(image)
        target_gadat = builder.resolve_iso_file(target_files, "GADAT032")
        target_gaml = builder.resolve_iso_file(target_files, "GAML")
        if target_gadat.size != source_gadat.size or target_gaml.size != source_gaml.size:
            raise SystemExit("GADAT032/GAML logical sizes differ from the Japanese ISO")
        target_gadat_begin = target_gadat.extent * builder.SECTOR
        target_gaml_begin = target_gaml.extent * builder.SECTOR

        for item in payload.get("entries", []):
            name = str(item["name"])
            primary_offset = int(item["primary_offset"])
            old_size = int(item["old_compressed_size"])
            new_size = int(item["new_compressed_size"])
            old_raw_size = int(item["old_raw_size"])
            new_raw_size = int(item["new_raw_size"])

            old_blob = source_gadat_data[primary_offset : primary_offset + old_size]
            if len(old_blob) != old_size:
                raise SystemExit(f"{name}: Japanese primary stream is truncated")
            old_raw = validate_stream(old_blob, old_raw_size, old_size, f"{name} Japanese primary")
            old_raw_sha = hashlib.sha256(old_raw).hexdigest()

            new_blob = bytes(
                image[
                    target_gadat_begin + primary_offset :
                    target_gadat_begin + primary_offset + new_size
                ]
            )
            new_raw = validate_stream(new_blob, new_raw_size, new_size, f"{name} Korean primary")
            expected_raw_sha = str(item.get("raw_sha256", ""))
            if expected_raw_sha and hashlib.sha256(new_raw).hexdigest() != expected_raw_sha:
                raise SystemExit(f"{name}: Korean primary raw SHA-256 differs from image report")

            hits = source_gaml_streams.get(old_raw_sha, [])
            if not hits:
                continue

            optimal_blob: bytes | None = None
            hit_reports: list[dict] = []
            for relative, source_used, source_raw_size in hits:
                if source_raw_size != old_raw_size:
                    raise SystemExit(
                        f"{name}: GAML raw-size collision at {relative:#x}: "
                        f"{source_raw_size}!={old_raw_size}"
                    )
                capacity = slot_capacity(source_gaml_data, relative, source_used)
                gaml_blob = new_blob
                compression = "primary"
                if len(gaml_blob) > capacity:
                    if optimal_blob is None:
                        optimal_blob = ikusa_lz.compress_optimal(new_raw)
                    if len(optimal_blob) > capacity:
                        raise SystemExit(
                            f"{name}: Korean stream does not fit GAML slot at {relative:#x}: "
                            f"primary={len(new_blob)} optimal={len(optimal_blob)} capacity={capacity}"
                        )
                    gaml_blob = optimal_blob
                    compression = "optimal"

                absolute = target_gaml_begin + relative
                current_slot = bytes(image[absolute : absolute + capacity])
                try:
                    current_raw, current_used = ikusa_lz.decompress(current_slot)
                except Exception as exc:
                    raise SystemExit(
                        f"{name}: target GAML slot is not a valid LZ stream at {relative:#x}: {exc}"
                    ) from exc
                current_sha = hashlib.sha256(current_raw).hexdigest()
                new_raw_sha = hashlib.sha256(new_raw).hexdigest()
                if current_sha == new_raw_sha:
                    already_patched_slots += 1
                    status = "already_patched"
                    stored_size = current_used
                    compression = "existing"
                else:
                    if current_sha != old_raw_sha:
                        raise SystemExit(
                            f"{name}: target GAML raw data differs from both Japanese and Korean "
                            f"data at {relative:#x}"
                        )
                    before = current_slot
                    image[absolute : absolute + capacity] = bytes(capacity)
                    image[absolute : absolute + len(gaml_blob)] = gaml_blob
                    after = bytes(image[absolute : absolute + capacity])
                    changed_bytes += sum(left != right for left, right in zip(before, after))
                    patched_slots += 1
                    status = "patched"
                    stored_size = len(gaml_blob)

                hit_reports.append(
                    {
                        "relative_offset": relative,
                        "iso_offset": absolute,
                        "capacity": capacity,
                        "source_compressed_size": source_used,
                        "compressed_size": stored_size,
                        "compression": compression,
                        "status": status,
                    }
                )

            entries.append(
                {
                    "name": name,
                    "old_compressed_size": old_size,
                    "new_compressed_size": new_size,
                    "gaml_copies": hit_reports,
                }
            )
        image.flush()

        verified_slots = 0
        by_name = {str(item["name"]): item for item in payload.get("entries", [])}
        for entry in entries:
            item = by_name[entry["name"]]
            primary_offset = int(item["primary_offset"])
            new_size = int(item["new_compressed_size"])
            new_raw_size = int(item["new_raw_size"])
            primary_blob = bytes(
                image[
                    target_gadat_begin + primary_offset :
                    target_gadat_begin + primary_offset + new_size
                ]
            )
            primary_raw = validate_stream(
                primary_blob, new_raw_size, new_size, f"{entry['name']} primary readback"
            )
            for copy in entry["gaml_copies"]:
                absolute = int(copy["iso_offset"])
                gaml_size = int(copy["compressed_size"])
                gaml_blob = bytes(image[absolute : absolute + gaml_size])
                gaml_raw = validate_stream(
                    gaml_blob, new_raw_size, gaml_size, f"{entry['name']} GAML readback"
                )
                if gaml_raw != primary_raw:
                    raise SystemExit(f"{entry['name']}: GAML raw TEX differs from primary")
                verified_slots += 1

    report = {
        "schema": "moonlit-lovers-gaml-runtime-images/v1",
        "iso": str(iso_path),
        "original_iso": str(original_iso),
        "image_report": str(image_report),
        "translated_images_with_gaml_copies": len(entries),
        "patched_slots": patched_slots,
        "already_patched_slots": already_patched_slots,
        "verified_slots": verified_slots,
        "changed_bytes": changed_bytes,
        "entries": entries,
    }
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        f"GAML runtime images: images={len(entries)} patched={patched_slots} "
        f"already={already_patched_slots} verified={verified_slots}"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-iso", type=Path, required=True)
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--image-report", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    patch(args.original_iso, args.iso, args.image_report, args.report)


if __name__ == "__main__":
    main()
