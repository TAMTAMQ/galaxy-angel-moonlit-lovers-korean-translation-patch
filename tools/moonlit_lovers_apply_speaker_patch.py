#!/usr/bin/env python3
"""Safely transplant the previously verified speaker-name patch onto a newer ISO.

The script treats the known-good pair
  current_images ISO -> speakerfix ISO
as the authority for the exact byte changes.  It computes byte runs that differ
inside GADAT000.DAT, ADV.DAT, and IDX.DAT, checks that every to-be-changed byte
in the new target still equals the old/reference byte, and only then writes the
verified new byte.

Speaker strings are encoded with custom Shift-JIS codes whose meaning depends on
the embedded SLPM font map.  A raw-byte transplant is therefore safe only when
the target uses the exact same embedded SLPM_654.29 as the reference pair.  If
the font differs, this tool refuses the transplant and the speaker table must be
re-encoded with moonlit_lovers_speakers.py against the target's current map.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
from pathlib import Path
from typing import BinaryIO

SECTOR = 2048
CONTAINERS = ("GADAT000.DAT;1", "ADV.DAT;1", "IDX.DAT;1")
FONT_FILE = "SLPM_654.29;1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def root_files(path: Path) -> dict[str, tuple[int, int]]:
    """Return {ISO9660 name: (absolute byte offset, size)} for root files."""
    with path.open("rb") as f:
        f.seek(16 * SECTOR)
        pvd = f.read(SECTOR)
        if len(pvd) != SECTOR or pvd[0] != 1 or pvd[1:6] != b"CD001":
            raise RuntimeError(f"{path}: ISO9660 PVD not found")
        root = pvd[156:]
        rec_len = root[0]
        if rec_len < 34:
            raise RuntimeError(f"{path}: invalid root directory record")
        root_rec = root[:rec_len]
        extent = struct.unpack_from("<I", root_rec, 2)[0]
        size = struct.unpack_from("<I", root_rec, 10)[0]
        f.seek(extent * SECTOR)
        data = f.read(size)

    out: dict[str, tuple[int, int]] = {}
    pos = 0
    while pos < len(data):
        rec_len = data[pos]
        if rec_len == 0:
            pos = ((pos // SECTOR) + 1) * SECTOR
            continue
        rec = data[pos : pos + rec_len]
        if len(rec) != rec_len or rec_len < 34:
            raise RuntimeError(f"{path}: truncated ISO9660 directory record")
        extent = struct.unpack_from("<I", rec, 2)[0]
        size = struct.unpack_from("<I", rec, 10)[0]
        flags = rec[25]
        name_len = rec[32]
        name_raw = rec[33 : 33 + name_len]
        if name_raw not in (b"\x00", b"\x01") and not (flags & 0x02):
            name = name_raw.decode("ascii", "strict")
            out[name] = (extent * SECTOR, size)
        pos += rec_len
    return out


def differing_runs(
    before: BinaryIO,
    after: BinaryIO,
    before_offset: int,
    after_offset: int,
    size: int,
    block_size: int = 64 * 1024,
) -> list[tuple[int, int]]:
    """Return container-relative half-open byte runs where before != after."""
    runs: list[tuple[int, int]] = []
    open_start: int | None = None
    rel = 0
    while rel < size:
        n = min(block_size, size - rel)
        before.seek(before_offset + rel)
        after.seek(after_offset + rel)
        a = before.read(n)
        b = after.read(n)
        if len(a) != n or len(b) != n:
            raise RuntimeError("unexpected EOF while comparing reference ISOs")
        if a == b:
            if open_start is not None:
                runs.append((open_start, rel))
                open_start = None
            rel += n
            continue

        for i, (x, y) in enumerate(zip(a, b)):
            p = rel + i
            if x != y:
                if open_start is None:
                    open_start = p
            elif open_start is not None:
                runs.append((open_start, p))
                open_start = None
        rel += n
    if open_start is not None:
        runs.append((open_start, size))

    # Merge adjacent runs (including adjacency across comparison blocks).
    merged: list[tuple[int, int]] = []
    for start, end in runs:
        if merged and merged[-1][1] == start:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


def read_at(f: BinaryIO, offset: int, size: int) -> bytes:
    f.seek(offset)
    data = f.read(size)
    if len(data) != size:
        raise RuntimeError(f"unexpected EOF at 0x{offset:x} size={size}")
    return data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True, type=Path, help="known ISO before speaker patch")
    ap.add_argument("--after", required=True, type=Path, help="known-good ISO after speaker patch")
    ap.add_argument("--target", required=True, type=Path, help="new ISO that needs speaker patch")
    ap.add_argument("--output", type=Path, help="patched output ISO; required with --apply")
    ap.add_argument("--report", type=Path, help="JSON report path")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    for p in (args.before, args.after, args.target):
        if not p.is_file():
            raise SystemExit(f"missing ISO: {p}")
    if args.apply and args.output is None:
        raise SystemExit("--output is required with --apply")
    if args.output and args.output.resolve() == args.target.resolve():
        raise SystemExit("refusing in-place patch; use a separate --output")

    before_files = root_files(args.before)
    after_files = root_files(args.after)
    target_files = root_files(args.target)

    for files, label in (
        (before_files, "before"),
        (after_files, "after"),
        (target_files, "target"),
    ):
        if FONT_FILE not in files:
            raise RuntimeError(f"{label}: missing root file {FONT_FILE}")
    bfont_off, bfont_size = before_files[FONT_FILE]
    afont_off, afont_size = after_files[FONT_FILE]
    tfont_off, tfont_size = target_files[FONT_FILE]
    if len({bfont_size, afont_size, tfont_size}) != 1:
        raise RuntimeError("embedded SLPM size mismatch across speaker transplant inputs")
    with args.before.open("rb") as fb, args.after.open("rb") as fa, args.target.open("rb") as ft:
        before_font = read_at(fb, bfont_off, bfont_size)
        after_font = read_at(fa, afont_off, afont_size)
        target_font = read_at(ft, tfont_off, tfont_size)
    if before_font != after_font:
        raise RuntimeError(
            "reference speaker-patch pair also changes SLPM_654.29; refusing raw transplant"
        )
    if target_font != before_font:
        raise RuntimeError(
            "target embedded SLPM_654.29 differs from the speaker-patch reference. "
            "Raw custom-SJIS speaker bytes may decode as different Hangul; rebuild speaker.tbl "
            "with moonlit_lovers_speakers.py and the target's current font_map.json instead."
        )

    report: dict[str, object] = {
        "schema": "moonlit-lovers-speaker-transplant/v1",
        "before": str(args.before),
        "after": str(args.after),
        "target": str(args.target),
        "apply": bool(args.apply),
        "font_compatibility": {
            "filename": FONT_FILE,
            "sha256": hashlib.sha256(before_font).hexdigest(),
            "reference_before_after_equal": True,
            "target_matches_reference": True,
        },
        "containers": {},
    }

    all_patches: list[tuple[str, int, bytes, bytes]] = []
    with args.before.open("rb") as fb, args.after.open("rb") as fa, args.target.open("rb") as ft:
        for name in CONTAINERS:
            if name not in before_files or name not in after_files or name not in target_files:
                raise RuntimeError(f"missing root container {name}")
            boff, bsize = before_files[name]
            aoff, asize = after_files[name]
            toff, tsize = target_files[name]
            if bsize != asize:
                raise RuntimeError(f"{name}: before/after size mismatch {bsize} != {asize}")
            if tsize != bsize:
                raise RuntimeError(f"{name}: target size mismatch {tsize} != {bsize}")

            runs = differing_runs(fb, fa, boff, aoff, bsize)
            changed_bytes = 0
            mismatches: list[dict[str, object]] = []
            run_items: list[dict[str, object]] = []
            for start, end in runs:
                n = end - start
                old = read_at(fb, boff + start, n)
                new = read_at(fa, aoff + start, n)
                current = read_at(ft, toff + start, n)
                if current != old:
                    mismatches.append(
                        {
                            "offset": start,
                            "size": n,
                            "target_sha256": hashlib.sha256(current).hexdigest(),
                            "expected_before_sha256": hashlib.sha256(old).hexdigest(),
                        }
                    )
                else:
                    all_patches.append((name, toff + start, old, new))
                changed_bytes += n
                run_items.append(
                    {
                        "offset": start,
                        "size": n,
                        "before_sha256": hashlib.sha256(old).hexdigest(),
                        "after_sha256": hashlib.sha256(new).hexdigest(),
                    }
                )

            report["containers"][name] = {
                "size": bsize,
                "before_extent": boff,
                "after_extent": aoff,
                "target_extent": toff,
                "diff_runs": len(runs),
                "changed_bytes": changed_bytes,
                "target_precondition_mismatches": mismatches,
                "runs": run_items,
            }
            if mismatches:
                raise RuntimeError(
                    f"{name}: {len(mismatches)} patch run(s) overlap bytes changed in the newer target; aborting"
                )

    report["patch_runs"] = len(all_patches)
    report["changed_bytes"] = sum(len(new) for _, _, _, new in all_patches)
    report["target_sha256_before"] = sha256_file(args.target)

    if args.apply:
        assert args.output is not None
        args.output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.target, args.output)
        with args.output.open("r+b") as fo:
            for _name, abs_offset, _old, new in all_patches:
                fo.seek(abs_offset)
                fo.write(new)
            fo.flush()

        # Exact post-write verification for every transplanted run.
        with args.output.open("rb") as fo:
            for name, abs_offset, _old, new in all_patches:
                got = read_at(fo, abs_offset, len(new))
                if got != new:
                    raise RuntimeError(f"post-write verification failed for {name} at 0x{abs_offset:x}")
        report["output"] = str(args.output)
        report["output_sha256"] = sha256_file(args.output)
        report["verified_runs"] = len(all_patches)
    else:
        report["verified_runs"] = 0

    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
