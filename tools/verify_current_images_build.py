#!/usr/bin/env python3
"""Split verifier for the current-image Moonlit Lovers final build.

The monolithic integrated verifier can exceed the 300-second DevSpace command
limit. This wrapper invokes the same authoritative verification functions in
small phases so each phase can complete independently.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mmap
import struct
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import galaxy_angel_build as iso_builder
import moonlit_lovers_translate_all as build_all
import moonlit_lovers_verify_integrated as integrated

PIDX_MAGIC = b"PIDX0\0\0\0"
PIDX_NODE_OFFSET = 0x50
PIDX_NODE_SIZE = 24


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_baseline() -> dict:
    baseline_path = PROJECT / "build/current_image_baseline.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    current = build_all.authoritative_image_state()
    summary = build_all.image_state_summary(current)
    missing = sorted(set(baseline["files"]) - set(current))
    added = sorted(set(current) - set(baseline["files"]))
    changed = sorted(
        path for path in set(current) & set(baseline["files"])
        if current[path] != baseline["files"][path]
    )
    if missing or added or changed:
        raise SystemExit(
            f"image baseline mismatch: missing={len(missing)} added={len(added)} changed={len(changed)}"
        )
    if summary["file_count"] != baseline["file_count"] or summary["aggregate_sha256"] != baseline["aggregate_sha256"]:
        raise SystemExit("image baseline aggregate mismatch")
    return {
        "file_count": summary["file_count"],
        "aggregate_sha256": summary["aggregate_sha256"],
        "missing": [],
        "added": [],
        "changed": [],
    }


def verify_indexes_fast(iso: Path, stems: list[str]) -> dict[str, dict]:
    """Verify central IDX mirrors PIDX leaves without copying giant alias spans.

    Moonlit's rebuilt SCENARIO/SLG ISO directory entries deliberately span large
    backing regions.  The older verifier materializes the whole logical file,
    which can copy several GiB just to read the small PIDX node table.  Central
    IDX verification only needs each leaf's (offset, raw, compressed) tuple, so
    read those records directly from the mmap instead.
    """
    results: dict[str, dict] = {}
    with iso.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        files = iso_builder.iso_files(image)
        idx_item = iso_builder.resolve_iso_file(files, "IDX")
        idx_begin = idx_item.extent * iso_builder.SECTOR

        for stem in stems:
            item = iso_builder.resolve_iso_file(files, stem)
            begin = item.extent * iso_builder.SECTOR
            if bytes(image[begin : begin + 8]) != PIDX_MAGIC:
                raise SystemExit(f"{stem}: not a PIDX0 container")
            node_count = struct.unpack_from("<I", image, begin + 0x10)[0]
            table_end = PIDX_NODE_OFFSET + node_count * PIDX_NODE_SIZE
            if begin + table_end > len(image):
                raise SystemExit(f"{stem}: PIDX node table outside ISO")

            by_offset: dict[int, tuple[int, int]] = {}
            for index in range(node_count):
                record = begin + PIDX_NODE_OFFSET + index * PIDX_NODE_SIZE
                kind, _name_offset, _child_count, data_offset, raw_size, compressed_size = struct.unpack_from(
                    "<6I", image, record
                )
                if kind == 0:
                    value = (raw_size, compressed_size)
                    previous = by_offset.get(data_offset)
                    if previous is not None and previous != value:
                        raise SystemExit(
                            f"{stem}: conflicting duplicate PIDX leaf at {data_offset:#x}"
                        )
                    by_offset[data_offset] = value
                elif kind != 1:
                    raise SystemExit(f"{stem}: unknown PIDX node type {kind} at node {index}")

            wanted = {(offset, raw, compressed) for offset, (raw, compressed) in by_offset.items()}
            candidates: dict[int, set[tuple[int, int, int]]] = {}
            for relative in range(0, idx_item.size - 15, 4):
                file_id, offset, raw_size, compressed_size = struct.unpack_from(
                    "<IIII", image, idx_begin + relative
                )
                value = (offset, raw_size, compressed_size)
                if value in wanted:
                    candidates.setdefault(file_id, set()).add(value)

            if candidates:
                ranked = sorted(candidates.items(), key=lambda row: len(row[1]), reverse=True)
                file_id, matches = ranked[0]
                ambiguous = len(ranked) > 1 and len(ranked[1][1]) == len(matches)
            else:
                file_id, matches, ambiguous = None, set(), False

            result = {
                "container": stem,
                "pidx_leaves": len(by_offset),
                "file_id": file_id,
                "idx_matches": len(matches),
                "ambiguous_file_id": ambiguous,
                "complete": file_id is not None and not ambiguous and len(matches) == len(wanted),
            }
            status = "OK" if result["complete"] else "FAIL"
            print(
                f"{status} {stem}: pidx_leaves={result['pidx_leaves']} "
                f"file_id={result['file_id']} idx_matches={result['idx_matches']} "
                f"ambiguous={result['ambiguous_file_id']}"
            )
            if not result["complete"]:
                raise SystemExit(f"central IDX verification failed: {stem}")
            results[stem] = result
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--phase", choices=["images", "indexes", "strict", "baseline", "hash"], required=True)
    parser.add_argument("--container", action="append", default=[])
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    iso = args.iso.resolve()

    if args.phase == "images":
        reports = [
            PROJECT / "build/gadat030_image_patch_report.json",
            PROJECT / "build/gadat031_image_patch_report.json",
            PROJECT / "build/gadat032_image_patch_report.json",
            PROJECT / "build/slg_image_patch_report.json",
        ]
        result = build_all.verify_image_reports(iso, reports)
    elif args.phase == "indexes":
        stems = args.container or ["SCENARIO", "SLG", "GADAT000", "GADAT030", "GADAT031", "GADAT032"]
        result = verify_indexes_fast(iso, stems)
    elif args.phase == "strict":
        if not args.container:
            raise SystemExit("--phase strict requires at least one --container")
        result = integrated.strict_resource_verification(iso, args.container)
    elif args.phase == "baseline":
        result = verify_baseline()
    else:
        result = {"size": iso.stat().st_size, "sha256": sha256_file(iso)}

    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
