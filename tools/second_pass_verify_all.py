#!/usr/bin/env python3
"""Corpus-wide integrity check to run after every edit (or batch of edits)
made during the 2nd-pass detail QA of the translation (see STATUS.md,
"2026-09-13 세션 인계").

Checks, across every assets/translation/segments/*.json file:
  - total file count and total unit count (should stay 139 / 25510 — a
    change here means a unit was added/removed/renamed, which should never
    happen during a text-only QA pass)
  - 0 dialogue (channel 1) units with any line wider than 40 display columns
    (fullwidth-aware column counting, matching the in-game font metrics)
  - 0 dialogue (channel 1) units with more than 3 lines
  - 0 units containing a literal backslash (would indicate a broken escape
    from a prior automated edit)

Usage:
    python second_pass_verify_all.py
"""
import glob
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SEG_DIR = os.path.join(PROJECT_ROOT, "assets", "translation", "segments")


def col_width(s):
    w = 0
    for ch in s:
        code = ord(ch)
        if code < 0x0300 or (0xFF61 <= code <= 0xFFDC) or (0xFFE8 <= code <= 0xFFEE):
            w += 1
        else:
            w += 2
    return w


def main():
    files = glob.glob(os.path.join(SEG_DIR, "*.json"))
    total_units = 0
    overflow_cols = 0
    overflow_lines = 0
    backslash = 0
    for f in files:
        data = json.load(open(f, encoding="utf-8"))
        for u in data["units"]:
            total_units += 1
            tr = u.get("translation") or ""
            if "\\" in tr:
                backslash += 1
            if u.get("channel") == 1:
                real_lines = tr.rstrip("\n").split("\n")
                if len(real_lines) > 3:
                    overflow_lines += 1
                for l in real_lines:
                    if col_width(l) > 40:
                        overflow_cols += 1
                        break

    print("files:", len(files))
    print("total units:", total_units)
    print("units with a line exceeding 40 cols:", overflow_cols)
    print("units with more than 3 lines:", overflow_lines)
    print("total with literal backslash:", backslash)


if __name__ == "__main__":
    main()
