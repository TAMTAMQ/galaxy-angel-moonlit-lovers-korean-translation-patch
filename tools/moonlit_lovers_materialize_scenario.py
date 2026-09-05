#!/usr/bin/env python3
"""Materialize Moonlit Lovers translated SCENARIO leaves.

This is intentionally separate from ``galaxy_angel_translation.py apply``.
The first Galaxy Angel build keeps every decompressed scenario leaf at its
original byte size.  Moonlit Lovers' PIDX builder stores and mirrors a new
``raw_size`` for rebuilt leaves, so this tool allows decompressed leaves to grow
or shrink while preserving the original script syntax and symbolic IDS labels.

It does not translate anything.  It only consumes already-approved dialogue and
selection assets plus an encoding map and writes rebuilt ``*_DAT_*.txt`` files
for ``moonlit_lovers_build.py``.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import galaxy_angel_translation as ga


SAVE_LABEL_RE = re.compile(r"\\SaveLabel\((?P<label>[^\r\n]*)\)")


def mission_layout_overrides(asset_dir: Path) -> dict[str, str]:
    path = asset_dir / "mission_layout_overrides.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, str] = {}
    for entry in payload.get("entries", []):
        original = str(entry["original"])
        translation = str(entry["translation"])
        if original in result:
            raise SystemExit(f"duplicate mission-layout original: {original!r}")
        if not translation.endswith("\n"):
            raise SystemExit(f"mission-layout translation must end with LF: {original!r}")
        result[original] = ga.normalize_display_punctuation(translation)
    return result


def save_label_translations(asset_dir: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(asset_dir.glob("save_label_translations*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for entry in payload.get("entries", []):
            original = str(entry["original"])
            translation = ga.normalize_display_punctuation(str(entry["translation"]))
            if original in result:
                raise SystemExit(f"duplicate SaveLabel original: {original!r}")
            if not translation:
                raise SystemExit(f"empty SaveLabel translation: {original!r}")
            result[original] = translation
    return result


def replace_save_labels(
    text: str,
    translations: dict[str, str],
    applied: set[str],
) -> str:
    if not translations:
        return text

    def replace(match: re.Match[str]) -> str:
        label = match.group("label")
        translated = translations.get(label)
        if translated is None:
            return match.group(0)
        applied.add(label)
        return f"\\SaveLabel({translated})"

    return SAVE_LABEL_RE.sub(replace, text)


def selection_translations(asset_dir: Path) -> dict[str, str]:
    explicit = asset_dir / "selection_translations.json"
    units_path = asset_dir / "selection_units.json"
    if explicit.is_file():
        payload = json.loads(explicit.read_text(encoding="utf-8"))
        return {
            key: ga.normalize_display_punctuation(value)
            for key, value in payload.get("translations", {}).items()
        }
    if units_path.is_file():
        payload = json.loads(units_path.read_text(encoding="utf-8"))
        return {
            unit["original"]: ga.normalize_display_punctuation(unit["translation"])
            for unit in payload.get("units", [])
            if unit.get("use_translation") and unit.get("translation")
        }
    return {}


def replace_selection_rows_moonlit(
    text: str,
    translations: dict[str, str],
    custom_map: dict[str, bytes],
    max_bytes: int,
    keep_overflow_original: bool,
    overflows: list[dict],
) -> str:
    """Translate Moonlit CRLF selection rows up to the runtime copy limit.

    Unlike the 1st-game helper, rows may grow beyond the Japanese source byte
    length because Moonlit's containing scenario leaf is rebuilt with a new
    raw_size.  The selection handler copies at most ``max_bytes`` bytes from one
    row; rows beyond that limit are either rejected or explicitly kept Japanese
    for a structure-only WIP build.
    """
    if not translations:
        return text

    def replace_block(match):
        rows = match.group(0).splitlines(keepends=True)
        output: list[str] = []
        for index, row in enumerate(rows):
            ending = ""
            content = row
            if content.endswith("\r\n"):
                content, ending = content[:-2], "\r\n"
            elif content.endswith("\n"):
                content, ending = content[:-1], "\n"
            if index == 0 or content == "@)ss":
                output.append(row)
                continue
            translated = translations.get(content)
            if translated is None:
                output.append(row)
                continue
            encoded_size = len(ga.encode_text(translated, custom_map))
            if encoded_size > max_bytes:
                overflows.append(
                    {
                        "original": content,
                        "translation": translated,
                        "encoded_bytes": encoded_size,
                        "limit": max_bytes,
                    }
                )
                if keep_overflow_original:
                    output.append(row)
                    continue
                raise SystemExit(
                    "Moonlit selection exceeds runtime row limit: "
                    f"{content!r}: {encoded_size}>{max_bytes}"
                )
            output.append(translated + ending)
        return "".join(output)

    return ga.SELECTION_BLOCK_RE.sub(replace_block, text)


def materialize(
    source_dir: Path,
    asset_dir: Path,
    output_dir: Path,
    encoding_map: Path,
    report_path: Path | None,
    selection_max_bytes: int,
    keep_selection_overflow_original: bool,
) -> dict:
    loaded = ga.validate(source_dir, asset_dir)
    custom_map = ga.load_custom_map(encoding_map)
    if custom_map is None:
        raise SystemExit("Moonlit scenario materialization requires --encoding-map")
    choices = selection_translations(asset_dir)
    mission_overrides = mission_layout_overrides(asset_dir)
    save_labels = save_label_translations(asset_dir)
    applied_mission_overrides: set[str] = set()
    applied_save_labels: set[str] = set()

    output_dir.mkdir(parents=True, exist_ok=True)
    written_names: set[str] = set()
    applied_dialogue = 0
    selection_only_files = 0
    changed_files = 0
    grown_files = 0
    shrunk_files = 0
    same_size_files = 0
    total_delta = 0
    file_report: list[dict] = []
    selection_overflows: list[dict] = []

    for segment, source in loaded:
        text = source["text"]
        cursor = 0
        pieces: list[str] = []
        for unit, match in zip(segment["units"], source["matches"], strict=True):
            pieces.append(text[cursor:match.start(2)])
            selected = unit["translation"] if unit["use_translation"] else unit["original"]
            if unit.get("use_translation") and int(unit.get("channel", -1)) == 0:
                mission_override = mission_overrides.get(unit["original"])
                if mission_override is not None:
                    selected = mission_override
                    applied_mission_overrides.add(unit["original"])
            pieces.append(selected.replace("\n", "\r\n"))
            cursor = match.end(2)
            applied_dialogue += int(unit["use_translation"])
        pieces.append(text[cursor:])
        rebuilt_text = replace_selection_rows_moonlit(
            "".join(pieces), choices, custom_map, selection_max_bytes,
            keep_selection_overflow_original, selection_overflows,
        )
        rebuilt_text = replace_save_labels(
            rebuilt_text, save_labels, applied_save_labels
        )
        rebuilt = ga.encode_scenario(rebuilt_text, custom_map)
        output_name = segment["source"]["path"]
        source_path = source_dir / output_name
        source_size = source_path.stat().st_size
        delta = len(rebuilt) - source_size
        (output_dir / output_name).write_bytes(rebuilt)
        written_names.add(output_name)
        changed_files += int(rebuilt != source_path.read_bytes())
        grown_files += int(delta > 0)
        shrunk_files += int(delta < 0)
        same_size_files += int(delta == 0)
        total_delta += delta
        file_report.append(
            {
                "file": output_name,
                "source_size": source_size,
                "rebuilt_size": len(rebuilt),
                "delta": delta,
                "dialogue_units": len(segment["units"]),
            }
        )

    # Choice-only leaves have no @N dialogue segment, so materialize them here.
    if choices:
        for path in sorted(source_dir.glob("*.txt")):
            if path.name in written_names:
                continue
            raw, source_text = ga.read_scenario(path)
            rebuilt_text = replace_selection_rows_moonlit(
                source_text, choices, custom_map, selection_max_bytes,
                keep_selection_overflow_original, selection_overflows,
            )
            rebuilt_text = replace_save_labels(
                rebuilt_text, save_labels, applied_save_labels
            )
            if rebuilt_text == source_text:
                continue
            rebuilt = ga.encode_scenario(rebuilt_text, custom_map)
            delta = len(rebuilt) - len(raw)
            (output_dir / path.name).write_bytes(rebuilt)
            selection_only_files += 1
            changed_files += 1
            grown_files += int(delta > 0)
            shrunk_files += int(delta < 0)
            same_size_files += int(delta == 0)
            total_delta += delta
            file_report.append(
                {
                    "file": path.name,
                    "source_size": len(raw),
                    "rebuilt_size": len(rebuilt),
                    "delta": delta,
                    "dialogue_units": 0,
                    "selection_only": True,
                }
            )

    missing_save_labels = sorted(set(save_labels) - applied_save_labels)
    if missing_save_labels:
        raise SystemExit(
            "SaveLabel translations not found in scenario assets: "
            + ", ".join(repr(value) for value in missing_save_labels)
        )

    missing_mission_overrides = sorted(set(mission_overrides) - applied_mission_overrides)
    if missing_mission_overrides:
        raise SystemExit(
            "mission-layout override originals not found in scenario assets: "
            + ", ".join(repr(value) for value in missing_mission_overrides)
        )

    report = {
        "schema": "moonlit-lovers-scenario-materialize/v1",
        "mission_layout_override_patterns": len(mission_overrides),
        "mission_layout_override_patterns_applied": len(applied_mission_overrides),
        "save_label_translation_patterns": len(save_labels),
        "save_label_translation_patterns_applied": len(applied_save_labels),
        "applied_dialogue_units": applied_dialogue,
        "selection_translations": len(choices),
        "segment_files": len(loaded),
        "selection_only_files": selection_only_files,
        "written_files": len(file_report),
        "changed_files": changed_files,
        "grown_files": grown_files,
        "shrunk_files": shrunk_files,
        "same_size_files": same_size_files,
        "total_raw_size_delta": total_delta,
        "selection_max_bytes": selection_max_bytes,
        "selection_overflow_count": len(selection_overflows),
        "selection_overflows": selection_overflows,
        "files": file_report,
    }
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        f"materialized {len(file_report)} files; dialogue={applied_dialogue} "
        f"selections={len(choices)} selection_only={selection_only_files} "
        f"grown={grown_files} shrunk={shrunk_files} same={same_size_files} "
        f"delta={total_delta:+d} selection_overflows={len(selection_overflows)}"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--encoding-map", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--selection-max-bytes", type=int, default=34)
    parser.add_argument(
        "--keep-selection-overflow-original",
        action="store_true",
        help="For structure-only WIP builds, keep rows over the runtime byte limit in Japanese.",
    )
    args = parser.parse_args()
    materialize(
        args.source,
        args.assets,
        args.output,
        args.encoding_map,
        args.report,
        args.selection_max_bytes,
        args.keep_selection_overflow_original,
    )


if __name__ == "__main__":
    main()
