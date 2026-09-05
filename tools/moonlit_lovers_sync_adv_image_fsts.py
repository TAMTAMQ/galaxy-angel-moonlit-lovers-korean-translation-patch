#!/usr/bin/env python3
"""Synchronize ADV FSTS compressed-size metadata for patched runtime images.

The generic image patcher replaces byte-identical runtime copies in ADV in
place. Some of those runtime copies are themselves FSTS resources. The image
stream can become shorter/longer while still fitting the fixed runtime slot,
so the FSTS record's compressed_size must be updated as well. This tool only
changes the 4-byte compressed_size field of FSTS records whose data offset is
explicitly listed by the image patch reports.

No image data, raw size, resource offset, resource count, or unrelated bytes
are changed.
"""
from __future__ import annotations

import argparse
import json
import mmap
import struct
from pathlib import Path

import galaxy_angel_build as builder
import ikusa_lz
import moonlit_lovers_resources as resources


def load_runtime_targets(report_paths: list[Path], adv_begin: int) -> dict[int, dict]:
    targets: dict[int, dict] = {}
    for report_path in report_paths:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        for entry in payload.get("entries", []):
            expected_size = int(entry["new_compressed_size"])
            for runtime in entry.get("runtime_copies", []):
                if str(runtime.get("container", "")).upper() != "ADV":
                    continue
                absolute = int(runtime["iso_offset"])
                relative = absolute - adv_begin
                if relative < 0:
                    raise SystemExit(
                        f"runtime hit precedes ADV: {entry['name']} {absolute:#x}"
                    )
                prior = targets.get(relative)
                current = {
                    "name": entry["name"],
                    "expected_compressed_size": expected_size,
                    "absolute_iso_offset": absolute,
                }
                if prior is not None and prior["expected_compressed_size"] != expected_size:
                    raise SystemExit(
                        f"conflicting runtime compressed sizes at {relative:#x}: "
                        f"{prior['expected_compressed_size']} != {expected_size}"
                    )
                targets[relative] = current
    return targets


def sync(iso_path: Path, report_paths: list[Path], report_path: Path | None = None) -> dict:
    with iso_path.open("r+b") as stream, mmap.mmap(stream.fileno(), 0) as image:
        files = builder.iso_files(image)
        item = builder.resolve_iso_file(files, "ADV")
        adv_begin = item.extent * builder.SECTOR
        container = bytearray(image[adv_begin : adv_begin + item.size])
        before_container = bytes(container)
        targets = load_runtime_targets(report_paths, adv_begin)
        grouped = {item.offset: item for item in resources.fsts_resources(container, "ADV")}

        matched = 0
        changed_records = 0
        already_synced_records = 0
        non_fsts_runtime_copies = 0
        entries: list[dict] = []
        allowed_absolute_fields: set[int] = set()

        for offset, target in sorted(targets.items()):
            resource = grouped.get(offset)
            if resource is None:
                non_fsts_runtime_copies += 1
                continue
            matched += 1
            if resource.codec != "ikusa_lz":
                raise SystemExit(
                    f"ADV runtime image is not Ikusa LZ at {offset:#x}: {resource.codec}"
                )
            raw, used = ikusa_lz.decompress(container, offset)
            expected = target["expected_compressed_size"]
            if used != expected:
                raise SystemExit(
                    f"runtime stream size disagrees with image report at {offset:#x}: "
                    f"{used}!={expected}"
                )
            if len(raw) != resource.raw_size:
                raise SystemExit(
                    f"runtime raw size disagrees with FSTS at {offset:#x}: "
                    f"{len(raw)}!={resource.raw_size}"
                )
            old_size = resource.compressed_size
            for record in resource.record_positions:
                field = record + 12
                allowed_absolute_fields.update(
                    range(adv_begin + field, adv_begin + field + 4)
                )
                current = struct.unpack_from("<I", container, field)[0]
                if current == used:
                    already_synced_records += 1
                    continue
                if current != old_size:
                    raise SystemExit(
                        f"unexpected FSTS size before sync at {offset:#x}: "
                        f"record={current} grouped={old_size}"
                    )
                struct.pack_into("<I", container, field, used)
                changed_records += 1
            entries.append(
                {
                    "name": target["name"],
                    "offset": offset,
                    "raw_size": resource.raw_size,
                    "old_compressed_size": old_size,
                    "new_compressed_size": used,
                    "record_positions": resource.record_positions,
                }
            )

        image[adv_begin : adv_begin + item.size] = container
        image.flush()

    # The only write above is the ADV ISO extent. Compare that bounded extent rather than
    # materializing and byte-scanning the entire multi-gigabyte disc image twice.
    changed_positions = [
        adv_begin + index
        for index, (left, right) in enumerate(zip(before_container, container))
        if left != right
    ]
    unexpected = [index for index in changed_positions if index not in allowed_absolute_fields]
    if unexpected:
        raise SystemExit(
            f"ADV FSTS sync changed bytes outside compressed-size fields: "
            f"{unexpected[:16]}"
        )

    # Re-open and require strict resource-table/decompressor agreement for all ADV resources.
    with iso_path.open("rb") as stream, mmap.mmap(
        stream.fileno(), 0, access=mmap.ACCESS_READ
    ) as image:
        files = builder.iso_files(image)
        item = builder.resolve_iso_file(files, "ADV")
        adv_begin = item.extent * builder.SECTOR
        container = bytes(image[adv_begin : adv_begin + item.size])
        final_resources = resources.fsts_resources(container, "ADV")
        strict_verified = 0
        for resource in final_resources:
            resources.decompress_resource(
                container,
                resource.offset,
                resource.raw_size,
                resource.compressed_size,
            )
            strict_verified += 1

    report = {
        "schema": "moonlit-lovers-adv-image-fsts-sync/v1",
        "iso": str(iso_path),
        "image_reports": [str(path) for path in report_paths],
        "runtime_unique_offsets": len(targets),
        "matched_fsts_resources": matched,
        "non_fsts_runtime_copies": non_fsts_runtime_copies,
        "changed_records": changed_records,
        "already_synced_records": already_synced_records,
        "changed_bytes": len(changed_positions),
        "strict_adv_resources_verified": strict_verified,
        "entries": entries,
    }
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        f"ADV runtime image FSTS sync: runtime={len(targets)} fsts={matched} "
        f"records_changed={changed_records} strict_verified={strict_verified}"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--image-report", type=Path, action="append", required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    sync(args.iso, args.image_report, args.report)


if __name__ == "__main__":
    main()
