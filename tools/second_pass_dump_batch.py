#!/usr/bin/env python3
"""Dump original/translation pairs from a batch of segment JSON files to a
single flat text file for sequential human/manual review during the 2nd-pass
detail QA of the translation (see STATUS.md, "2026-09-13 세션 인계").

Usage:
    python second_pass_dump_batch.py <out_path.txt> <SCENARIO_DAT_xxx.json> [...]

Reads each named file from assets/translation/segments/ (relative to this
script's parent's parent, i.e. the project root) and writes:

    ===== <filename> (<N> units) =====
    <short_id>\tch<channel>\tJP: <original with literal \\n>
    <short_id>\tch<channel>\tKO: <translation with literal \\n>
    ...

for every unit, in file order, one file after another. This lets a reviewer
Read() the dump in manageable chunks (e.g. offset/limit of ~400 lines) and
compare original vs translation side by side without opening each JSON file
individually.
"""
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SEG_DIR = os.path.join(PROJECT_ROOT, "assets", "translation", "segments")


def dump_one(fname, out):
    path = os.path.join(SEG_DIR, fname)
    data = json.load(open(path, encoding="utf-8"))
    out.write(f"\n===== {fname} ({len(data['units'])} units) =====\n")
    for u in data["units"]:
        orig = (u.get("original") or "").replace("\n", "\\n")
        tr = (u.get("translation") or "").replace("\n", "\\n")
        ch = u.get("channel")
        short_id = u["id"].split(":")[-1]
        out.write(f"{short_id}\tch{ch}\tJP: {orig}\n")
        out.write(f"{short_id}\tch{ch}\tKO: {tr}\n")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    out_path = sys.argv[1]
    fnames = sys.argv[2:]
    with open(out_path, "w", encoding="utf-8") as out:
        for fname in fnames:
            dump_one(fname, out)
    print(f"wrote {out_path}")
