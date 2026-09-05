#!/usr/bin/env python3
from __future__ import annotations

import argparse
import mmap
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

import galaxy_angel_build as builder
import moonlit_lovers_resources as resources

NAME_RE = re.compile(r"^SCENARIO_DAT_([0-9a-fA-F]{8})\.txt$")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--original-iso", type=Path, required=True)
    parser.add_argument("--names-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    wanted: list[tuple[str, int]] = []
    for path in sorted(args.names_dir.glob("SCENARIO_DAT_*.txt")):
        match = NAME_RE.match(path.name)
        if not match:
            continue
        wanted.append((path.name, int(match.group(1), 16)))
    if not wanted:
        raise SystemExit("no SCENARIO_DAT_*.txt files found in --names-dir")

    args.output.mkdir(parents=True, exist_ok=True)
    with args.original_iso.open("rb") as original_stream, mmap.mmap(original_stream.fileno(), 0, access=mmap.ACCESS_READ) as original_image:
        original_files = builder.iso_files(original_image)
        original_item = builder.resolve_iso_file(original_files, "SCENARIO")
        original_begin = original_item.extent * builder.SECTOR
        original_container = bytes(original_image[original_begin:original_begin + original_item.size])
        original_recs = resources.pidx_record_map(original_container, "SCENARIO")
        wanted_records: dict[int, tuple[str, int]] = {}
        for name, offset in wanted:
            if offset not in original_recs:
                raise SystemExit(f"missing pristine SCENARIO PIDX offset {offset:#x} for {name}")
            record, _raw_size, _compressed_size = original_recs[offset]
            wanted_records[record] = (name, offset)

    with args.iso.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        files = builder.iso_files(image)
        item = builder.resolve_iso_file(files, "SCENARIO")
        begin = item.extent * builder.SECTOR
        container = bytes(image[begin:begin + item.size])
        current_recs = resources.pidx_record_map(container, "SCENARIO")
        by_record = {
            record: (offset, raw_size, compressed_size)
            for offset, (record, raw_size, compressed_size) in current_recs.items()
        }
        for record, (name, original_offset) in wanted_records.items():
            if record not in by_record:
                raise SystemExit(
                    f"missing current SCENARIO PIDX record {record:#x} for {name} "
                    f"(pristine offset {original_offset:#x})"
                )
            current_offset, raw_size, compressed_size = by_record[record]
            raw = resources.decompress_resource(
                container, current_offset, raw_size, compressed_size
            )
            (args.output / name).write_bytes(raw)

    print(f"extracted {len(wanted)} current SCENARIO baselines to {args.output}")


if __name__ == "__main__":
    main()
