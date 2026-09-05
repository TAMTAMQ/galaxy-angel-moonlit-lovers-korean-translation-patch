#!/usr/bin/env python3
"""List user-visible COM_n strings from Moonlit Lovers ship-movement TBI tables.

This is a read-only audit helper.  It decodes the extracted TBI resources as CP932
and prints unique non-empty COM_n values with their source locations.
"""

from __future__ import annotations

import collections
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
TBI_ROOT = PROJECT / "assets/full_extraction/SCENARIO/raw/dat/scenario"
MANIFEST = PROJECT / "assets/full_extraction/SCENARIO/manifest.json"
MISSION_OVERRIDES = PROJECT / "assets/translation/mission_layout_overrides.json"
SEGMENT_ROOT = PROJECT / "assets/translation/segments"


def main() -> None:
    mission_payload = json.loads(MISSION_OVERRIDES.read_text(encoding="utf-8"))
    mission_originals = {str(item["original"]) for item in mission_payload.get("entries", [])}
    channel0_originals: list[str] = []
    for path in sorted(SEGMENT_ROOT.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for unit in payload.get("units", []):
            if int(unit.get("channel", -1)) == 0:
                channel0_originals.append(str(unit.get("original", "")))
    matched_patterns = mission_originals & set(channel0_originals)
    matched_units = sum(original in mission_originals for original in channel0_originals)
    print(
        f"mission_override_patterns={len(mission_originals)} "
        f"matched_patterns={len(matched_patterns)} matched_units={matched_units} "
        f"missing_patterns={len(mission_originals - matched_patterns)}"
    )
    for original in sorted(mission_originals - matched_patterns):
        print(f"MISSING_MISSION\t{original!r}")

    values: dict[str, list[dict[str, object]]] = collections.defaultdict(list)
    for path in sorted(TBI_ROOT.glob("tbi_*.tbl")):
        text = path.read_text(encoding="cp932")
        for line_number, line in enumerate(text.splitlines(), 1):
            if not line.startswith("COM_") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if not value:
                continue
            values[value].append(
                {
                    "file": path.name,
                    "line": line_number,
                    "key": key,
                }
            )

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    resource_by_name = {
        str(item["name"]): item
        for item in manifest.get("resources", [])
        if str(item.get("name", "")).lower().startswith("tbi_")
    }
    print(
        f"files={len(list(TBI_ROOT.glob('tbi_*.tbl')))} "
        f"unique_nonempty_com={len(values)} "
        f"occurrences={sum(len(items) for items in values.values())}"
    )
    for name in sorted(resource_by_name):
        item = resource_by_name[name]
        print(
            f"RESOURCE\t{name}\t{int(item['offset'])}\t{item['raw_sha256']}\t"
            f"{int(item['raw_size'])}\t{int(item['compressed_size'])}"
        )
    for number, (text, items) in enumerate(sorted(values.items()), 1):
        locations = ", ".join(
            f"{item['file']}:{item['line']}:{item['key']}" for item in items
        )
        print(f"{number:03d}\t{len(items):3d}\t{text}\t{locations}")


if __name__ == "__main__":
    main()
