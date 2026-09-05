#!/usr/bin/env python3
"""Targeted verifier for the 2026-09-05 font/speaker regression fix.

The previous v1.5 ISO is already covered by the expensive integrated verifier.
This verifier proves that the follow-up ISO changes only the four files that are
allowed for this fix (embedded ELF, speaker containers, and central IDX), then
re-validates the exact runtime speaker resources and all compressed resources in
ADV/GADAT000.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mmap
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

import galaxy_angel_build as builder
import moonlit_lovers_resources as resources

ALLOWED_CHANGED_BASENAMES = {"SLPM_654.29", "GADAT000.DAT", "ADV.DAT", "IDX.DAT"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compare_iso_files(before: Path, after: Path) -> dict:
    """Prove every changed physical byte falls inside one of four allowed files.

    Moonlit's rebuilt SCENARIO/SLG ISO directory sizes intentionally span backing
    regions and therefore overlap later files.  Comparing those logical file spans
    would falsely report ADV/IDX changes as SCENARIO/SLG changes.  Absolute physical
    diff ranges avoid that aliasing and are the stronger check for this patch.
    """
    if before.stat().st_size != after.stat().st_size:
        raise SystemExit("ISO size changed")

    with before.open("rb") as before_stream, mmap.mmap(
        before_stream.fileno(), 0, access=mmap.ACCESS_READ
    ) as before_image, after.open("rb") as after_stream, mmap.mmap(
        after_stream.fileno(), 0, access=mmap.ACCESS_READ
    ) as after_image:
        before_files = builder.iso_files(before_image)
        after_files = builder.iso_files(after_image)
        if set(before_files) != set(after_files):
            raise SystemExit("ISO file inventory changed")
        for name in sorted(before_files):
            old = before_files[name]
            new = after_files[name]
            if (old.extent, old.size) != (new.extent, new.size):
                raise SystemExit(
                    f"ISO file layout changed for {name}: "
                    f"{(old.extent, old.size)} != {(new.extent, new.size)}"
                )

        allowed: dict[str, tuple[int, int]] = {}
        for basename in sorted(ALLOWED_CHANGED_BASENAMES):
            matches = [
                item for key, item in after_files.items()
                if key.rsplit("/", 1)[-1] == basename
            ]
            if len(matches) != 1:
                raise SystemExit(f"allowed ISO file resolution failed for {basename}: {len(matches)}")
            item = matches[0]
            begin = item.extent * builder.SECTOR
            allowed[basename] = (begin, begin + item.size)

        runs: list[tuple[int, int]] = []
        open_start: int | None = None
        chunk_size = 8 * 1024 * 1024
        size_total = len(before_image)
        for chunk_start in range(0, size_total, chunk_size):
            chunk_end = min(size_total, chunk_start + chunk_size)
            a = before_image[chunk_start:chunk_end]
            b = after_image[chunk_start:chunk_end]
            if a == b:
                if open_start is not None:
                    runs.append((open_start, chunk_start))
                    open_start = None
                continue
            for index, (old_byte, new_byte) in enumerate(zip(a, b)):
                absolute = chunk_start + index
                if old_byte != new_byte:
                    if open_start is None:
                        open_start = absolute
                elif open_start is not None:
                    runs.append((open_start, absolute))
                    open_start = None
        if open_start is not None:
            runs.append((open_start, size_total))

        outside = []
        touched = {name: 0 for name in allowed}
        for start, end in runs:
            owners = [name for name, (a, b) in allowed.items() if start >= a and end <= b]
            if not owners:
                outside.append({"start": start, "end": end, "size": end - start})
                continue
            for name in owners:
                touched[name] += end - start
        if outside:
            raise SystemExit(f"changed bytes outside allowed physical files: {outside[:10]}")
        missing_touches = sorted(name for name, count in touched.items() if count == 0)
        if missing_touches:
            raise SystemExit(f"expected changed physical file(s) were untouched: {missing_touches}")

        changed_files = []
        for basename, (begin, end) in allowed.items():
            changed_files.append(
                {
                    "path": basename,
                    "extent_begin": begin,
                    "size": end - begin,
                    "changed_bytes": touched[basename],
                    "before_sha256": sha256_bytes(bytes(before_image[begin:end])),
                    "after_sha256": sha256_bytes(bytes(after_image[begin:end])),
                }
            )

    return {
        "physical_diff_runs": len(runs),
        "physical_changed_bytes": sum(end - start for start, end in runs),
        "changed_files": changed_files,
        "changed_basenames": sorted(allowed),
        "only_allowed_physical_ranges_changed": True,
    }


def load_container(image: mmap.mmap, files: dict[str, builder.IsoFile], stem: str) -> bytes:
    item = builder.resolve_iso_file(files, stem)
    begin = item.extent * builder.SECTOR
    return bytes(image[begin : begin + item.size])


def one_resource(container: bytes, stem: str, offset: int) -> resources.Resource:
    matches = [item for item in resources.container_resources(container, stem) if item.offset == offset]
    if len(matches) != 1:
        raise SystemExit(f"{stem} {offset:#x}: expected exactly one resource, got {len(matches)}")
    return matches[0]


def strict_verify_container(container: bytes, stem: str) -> int:
    rows = resources.container_resources(container, stem)
    for row in rows:
        raw = resources.decompress_resource(
            container, row.offset, row.raw_size, row.compressed_size
        )
        if len(raw) != row.raw_size:
            raise SystemExit(
                f"{stem} strict decompress size mismatch at {row.offset:#x}: "
                f"{len(raw)} != {row.raw_size}"
            )
    return len(rows)


def verify_runtime(
    iso: Path,
    font_elf: Path,
    speaker_spec: Path,
    speaker_report: Path,
) -> dict:
    spec = json.loads(speaker_spec.read_text(encoding="utf-8"))
    report = json.loads(speaker_report.read_text(encoding="utf-8"))
    expected_raw_sha = str(report["patched_raw_sha256"])
    expected_font = font_elf.read_bytes()
    expected_font_sha = sha256_bytes(expected_font)

    with iso.open("rb") as stream, mmap.mmap(
        stream.fileno(), 0, access=mmap.ACCESS_READ
    ) as image:
        files = builder.iso_files(image)

        elf_item = files.get("SLPM_654.29")
        if elf_item is None:
            raise SystemExit("SLPM_654.29 missing from final ISO")
        elf_begin = elf_item.extent * builder.SECTOR
        embedded_elf = bytes(image[elf_begin : elf_begin + elf_item.size])
        if embedded_elf != expected_font:
            raise SystemExit("final embedded ELF does not match corrected font_wip")

        gad = load_container(image, files, "GADAT000")
        adv = load_container(image, files, "ADV")
        idx = load_container(image, files, "IDX")

        canonical_offset = int(spec["canonical"]["offset"])
        canonical = one_resource(gad, "GADAT000", canonical_offset)
        canonical_raw = resources.decompress_resource(
            gad, canonical.offset, canonical.raw_size, canonical.compressed_size
        )
        if sha256_bytes(canonical_raw) != expected_raw_sha:
            raise SystemExit("GADAT000 speaker.tbl raw hash mismatch")

        adv_rows = []
        for copy in spec["runtime_copies"]:
            offset = int(copy["offset"])
            row = one_resource(adv, "ADV", offset)
            raw = resources.decompress_resource(
                adv, row.offset, row.raw_size, row.compressed_size
            )
            raw_sha = sha256_bytes(raw)
            if raw_sha != expected_raw_sha:
                raise SystemExit(f"ADV speaker copy {offset:#x} raw hash mismatch")
            adv_rows.append(
                {
                    "offset": offset,
                    "raw_size": row.raw_size,
                    "compressed_size": row.compressed_size,
                    "raw_sha256": raw_sha,
                }
            )

        # The central runtime index must agree with the canonical local PIDX tuple.
        idx_hits = []
        file_id = int(report["canonical"]["idx_file_id"])
        for relative in range(0, len(idx) - 15, 4):
            row_file_id, offset, raw_size, compressed_size = struct.unpack_from(
                "<IIII", idx, relative
            )
            if row_file_id == file_id and offset == canonical.offset and raw_size == canonical.raw_size:
                idx_hits.append(
                    {
                        "relative": relative,
                        "file_id": row_file_id,
                        "offset": offset,
                        "raw_size": raw_size,
                        "compressed_size": compressed_size,
                    }
                )
        if len(idx_hits) != 1:
            raise SystemExit(f"IDX speaker tuple expected 1 hit, got {len(idx_hits)}")
        if idx_hits[0]["compressed_size"] != canonical.compressed_size:
            raise SystemExit(
                "IDX/local speaker compressed-size mismatch: "
                f"{idx_hits[0]['compressed_size']} != {canonical.compressed_size}"
            )

        strict = {
            "GADAT000": strict_verify_container(gad, "GADAT000"),
            "ADV": strict_verify_container(adv, "ADV"),
        }

    return {
        "embedded_font_sha256": expected_font_sha,
        "speaker_raw_sha256": expected_raw_sha,
        "canonical": {
            "offset": canonical.offset,
            "raw_size": canonical.raw_size,
            "compressed_size": canonical.compressed_size,
            "raw_sha256": sha256_bytes(canonical_raw),
        },
        "adv_runtime_copies": adv_rows,
        "idx": idx_hits[0],
        "strict_resource_verification": strict,
        "speaker_readback": "3/3",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--font-elf", type=Path, required=True)
    parser.add_argument("--speaker-spec", type=Path, required=True)
    parser.add_argument("--speaker-report", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    for path in (args.before, args.after, args.font_elf, args.speaker_spec, args.speaker_report):
        if not path.is_file():
            raise SystemExit(f"missing input: {path}")

    comparison = compare_iso_files(args.before, args.after)
    runtime = verify_runtime(args.after, args.font_elf, args.speaker_spec, args.speaker_report)
    payload = {
        "schema": "moonlit-lovers-font-speaker-targeted-verify/v1",
        "before_iso": str(args.before),
        "before_sha256": sha256_file(args.before),
        "after_iso": str(args.after),
        "after_sha256": sha256_file(args.after),
        "after_size": args.after.stat().st_size,
        "comparison": comparison,
        "runtime": runtime,
        "ok": True,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("TARGETED FONT/SPEAKER VERIFY OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
