#!/usr/bin/env python3
"""Read-only audit of Japanese string literals embedded in scenario commands."""

from __future__ import annotations

import collections
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / "source/scenario"
JAPANESE_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]")
COMMAND_RE = re.compile(r"\\(?P<command>[A-Za-z][A-Za-z0-9_]*)\((?P<args>[^\r\n)]*)\)")
SAVE_LABEL_RE = re.compile(r"\\SaveLabel\((?P<label>.*)\)")


def main() -> None:
    found: dict[tuple[str, str], list[tuple[str, int]]] = collections.defaultdict(list)
    by_command: collections.Counter[str] = collections.Counter()
    for path in sorted(SOURCE.glob("*.txt")):
        text = path.read_text(encoding="cp932")
        for line_number, line in enumerate(text.splitlines(), 1):
            save_match = SAVE_LABEL_RE.search(line)
            if save_match:
                label = save_match.group("label")
                if label:
                    found[("SaveLabel", label)].append((path.name, line_number))
                    by_command["SaveLabel"] += 1
                continue
            for match in COMMAND_RE.finditer(line):
                args = match.group("args")
                if not JAPANESE_RE.search(args):
                    continue
                command = match.group("command")
                found[(command, args)].append((path.name, line_number))
                by_command[command] += 1
    print(
        f"unique_command_literals={len(found)} occurrences={sum(len(v) for v in found.values())}"
    )
    for command, count in sorted(by_command.items()):
        unique = sum(1 for key in found if key[0] == command)
        print(f"COMMAND\t{command}\tunique={unique}\toccurrences={count}")
    for (command, args), occurrences in sorted(found.items()):
        locations = ", ".join(f"{name}:{line}" for name, line in occurrences[:8])
        print(f"LITERAL\t{command}\t{len(occurrences)}\t{args}\t{locations}")


if __name__ == "__main__":
    main()
