#!/usr/bin/env python3
"""Reflow Moonlit Lovers translations to the measured dialogue window.

The model translates a single flattened line without deciding line breaks; this
step lays the Korean text out at the measured width.  The line breaks the
original used are not fixed elements of the format, but the full-width space
that 266 units put on their continuation lines is, so that hanging indent is
re-applied after wrapping.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

INDENT = "　"


def columns(text: str) -> int:
    return sum(1 if ord(char) < 0x80 else 2 for char in text)


def split_hard(text: str, maximum: int) -> list[str]:
    output: list[str] = []
    current: list[str] = []
    width = 0
    for char in text:
        char_width = 1 if ord(char) < 0x80 else 2
        if current and width + char_width > maximum:
            output.append("".join(current))
            current, width = [], 0
        current.append(char)
        width += char_width
    if current or not output:
        output.append("".join(current))
    return output


def wrap_text(text: str, maximum: int) -> list[str]:
    """Wrap on spaces, falling back to a hard split for a single long run."""
    if columns(text) <= maximum:
        return [text]
    output: list[str] = []
    current = ""
    for word in text.split(" "):
        candidate = word if not current else current + " " + word
        if columns(candidate) <= maximum:
            current = candidate
            continue
        if current:
            output.append(current)
            current = ""
        chunks = split_hard(word, maximum)
        output.extend(chunks[:-1])
        current = chunks[-1]
    if current:
        output.append(current)
    return output


def unit_indent(original: str) -> tuple[str, str]:
    """Return the (first line, continuation line) indents the original uses.

    Two layouts appear in this game: 210 units prefix every line after the first
    with a full-width space, and 13 prefix only their first line.  Both are part
    of the intended layout, so they are re-applied after wrapping.
    """
    lines = [line for line in original.split("\n") if line.strip()]
    if not lines:
        return "", ""
    if lines[0].startswith(INDENT):
        return INDENT, ""
    if len(lines) > 1 and all(line.startswith(INDENT) for line in lines[1:]):
        return "", INDENT
    return "", ""


def reflow(translation: str, indents: tuple[str, str], maximum: int) -> str:
    """Lay one logical line of Korean out at the measured width."""
    text = " ".join(
        line.strip().lstrip(INDENT).strip()
        for line in translation.split("\n")
        if line.strip()
    )
    if not text:
        return translation
    first_indent, rest_indent = indents
    # Each indent eats into the room its own line has, so the first line and the
    # continuation lines are wrapped against different budgets.
    head = wrap_text(text, maximum - columns(first_indent))[0]
    rest = text[len(head):].lstrip()
    lines = [first_indent + head]
    if rest:
        lines += [rest_indent + line
                  for line in wrap_text(rest, maximum - columns(rest_indent))]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--max-columns", type=int, default=40)
    parser.add_argument("--dialogue-max-lines", type=int, default=3)
    parser.add_argument("--report", type=Path,
                        help="write units that still exceed the dialogue budget")
    args = parser.parse_args()

    changed_files = changed_units = 0
    overflow: list[dict] = []
    for path in sorted((args.assets / "segments").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for unit in payload["units"]:
            translation = unit.get("translation")
            if not translation or not translation.strip():
                continue
            laid_out = reflow(translation, unit_indent(unit["original"]), args.max_columns)
            if laid_out != translation:
                unit["translation"] = laid_out
                changed = True
                changed_units += 1
            lines = [line for line in laid_out.split("\n") if line.strip()]
            if (unit.get("channel") == 1 and args.dialogue_max_lines
                    and len(lines) > args.dialogue_max_lines):
                overflow.append({
                    "id": unit["id"],
                    "lines": len(lines),
                    "original": unit["original"],
                    "translation": laid_out,
                })
                # A dialogue that runs past the window is not safe to show, so it
                # must not reach the game until a shorter translation replaces it.
                if unit.get("use_translation"):
                    unit["use_translation"] = False
                    unit["state"] = "needs_human"
                    changed = True
        if changed:
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            changed_files += 1

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps({"max_columns": args.max_columns,
                        "dialogue_max_lines": args.dialogue_max_lines,
                        "count": len(overflow),
                        "units": overflow}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(f"reflowed {changed_units} translations in {changed_files} files; "
          f"{len(overflow)} dialogue units still exceed {args.dialogue_max_lines} lines")


if __name__ == "__main__":
    main()
