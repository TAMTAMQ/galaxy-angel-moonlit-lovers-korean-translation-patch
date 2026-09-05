#!/usr/bin/env python3
"""Build the per-container image sets for every copy of a translated texture.

A battle texture is not stored once.  ``SLG`` holds the copy the PIDX index names, and each
per-stage bank in ``SLGRES``/``SLGSTAGE`` — plus ``ADV`` — keeps its own, sometimes compressed
differently, sometimes with no name at all.  Patching only the named copy therefore leaves the
Japanese one on screen during a battle.

``assets/translation/images/image_units.json`` already records, for every unique picture, the
exact container and resource offset of each of its copies.  This tool turns that into one
translated-image set per container, addressed by offset, which the battle-bank patcher writes
through the bank's own FSTS record.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path



def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=Path("work/galaxy_angel_moonlit_lovers"))
    parser.add_argument("--container", action="append", default=None,
                        help="containers to mirror into; defaults to the FSTS-indexed ones")
    parser.add_argument("--pidx-container", action="append", default=None,
                        help="containers whose copies are reached through the PIDX image "
                             "patcher instead: their extra copies join that container's own "
                             "build inputs rather than the FSTS mirror set")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--targets", type=Path,
                        help="missing-target report naming the audit indices this run is about")
    parser.add_argument("--targets-only-container", action="append", default=None,
                        help="mirror only --targets units into this container, leaving copies "
                             "an existing build path already writes alone")
    parser.add_argument(
        "--preserve-existing-image-tree",
        action="store_true",
        help="never create missing PIDX source/translated PNGs; fail instead",
    )
    args = parser.parse_args()

    project = args.project
    containers = args.container or ["SLG", "SLGRES", "SLGSTAGE", "ADV"]
    units = json.loads((project / "assets/translation/images/image_units.json").read_text(encoding="utf-8"))
    units = units if isinstance(units, list) else units["units"]

    target_indices: set[int] | None = None
    if args.targets:
        payload = json.loads(args.targets.read_text(encoding="utf-8"))
        target_indices = set(payload["final_target_audit_indices"])
    restricted = set(args.targets_only_container or [])
    if restricted and target_indices is None:
        raise SystemExit("--targets-only-container needs --targets")

    # Where each translated PNG lives: the renderers write one per container, named after the
    # resource offset of the copy they were rendered from.
    translated: dict[str, Path] = {}
    for container in ("GADAT030", "GADAT031", "GADAT032", "SLG", "ADV"):
        root = project / "assets/image_extraction" / container / "japanese_images/translated_png"
        if not root.is_dir():
            continue
        for path in root.glob("*.png"):
            translated.setdefault(f"{container}:{path.name}", path)

    def rendered(unit: dict) -> Path | None:
        for occurrence in unit["occurrences"]:
            name = occurrence.get("resource_name")
            candidates = []
            if name:
                candidates.append(f"{occurrence['container']}:{Path(name).with_suffix('.png').name}")
            candidates.append(f"{occurrence['container']}:block_{int(occurrence['resource_offset']):08x}.png")
            candidates.append(f"{occurrence['container']}:{Path(occurrence['png']).name}")
            for key in candidates:
                if key in translated:
                    return translated[key]
        return None

    pidx_containers = set(args.pidx_container or [])
    manifests: dict[str, list[dict]] = {name: [] for name in containers if name not in pidx_containers}
    added_to_build: dict[str, int] = {name: 0 for name in pidx_containers}
    covered, uncovered = 0, []
    extra: dict[str, dict[str, dict]] = {}
    for unit in units:
        source = rendered(unit)
        if source is None:
            continue
        covered += 1
        for occurrence in unit["occurrences"]:
            container = occurrence["container"]
            if container not in manifests and container not in pidx_containers:
                continue
            if container in restricted and unit["audit_index"] not in target_indices:
                continue
            offset = int(occurrence["resource_offset"])
            png = f"block_{offset:08x}.png"
            images_root = project / "assets/image_extraction" / container / "japanese_images"
            if container in pidx_containers:
                # This container already has a PIDX patch stage keyed on japanese_images/png,
                # so an extra copy only has to become one more of its build inputs.  Writing it
                # through an FSTS record instead would overwrite the PIDX index.
                original = project / "assets/full_extraction" / container / "png" / occurrence["png"]
                source_png = images_root / "png" / png
                if not source_png.is_file():
                    if args.preserve_existing_image_tree:
                        raise SystemExit(
                            f"preserve-existing-image-tree: missing PIDX source PNG {source_png}"
                        )
                    source_png.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(original, source_png)
                    added_to_build[container] += 1
                target = images_root / "translated_png" / png
                if not target.is_file():
                    if args.preserve_existing_image_tree:
                        raise SystemExit(
                            f"preserve-existing-image-tree: missing PIDX translated PNG {target}"
                        )
                    shutil.copy2(source, target)
                extra.setdefault(container, {})[png] = {
                    "name": occurrence.get("resource_name"),
                    "png": png,
                    "translated_png": png,
                    "resource_path": occurrence.get("resource_path"),
                    "resource_offset": offset,
                    "classification": "moonlit-image-occurrence-copy",
                    "mirror_of": unit["canonical"].get("resource_name") or unit["canonical"]["png"],
                    "audit_index": unit["audit_index"],
                }
                continue
            (images_root / "mirror_png").mkdir(parents=True, exist_ok=True)
            target = images_root / "mirror_png" / png
            if target.resolve() != source.resolve():
                shutil.copy2(source, target)
            manifests[container].append({
                "png": png,
                "translated_png": png,
                "resource_offset": offset,
                "resource_path": occurrence.get("resource_path"),
                "name": occurrence.get("resource_name"),
                "mirror_of": unit["canonical"].get("resource_name") or unit["canonical"]["png"],
                "audit_index": unit["audit_index"],
                "classification": "moonlit-image-occurrence-mirror",
            })

    summary = {}
    for container, rows in manifests.items():
        rows.sort(key=lambda row: row["png"])
        path = project / "assets/image_extraction" / container / "japanese_images/mirror_manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary[container] = len(rows)

    for container, rows in extra.items():
        path = project / "assets/image_extraction" / container / "japanese_images/manifest.json"
        existing = {}
        if path.is_file():
            existing = {row["png"]: row for row in json.loads(path.read_text(encoding="utf-8"))}
        for png, row in rows.items():
            existing.setdefault(png, row)
        merged = sorted(existing.values(), key=lambda row: str(row.get("png", "")))
        path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
        summary[f"{container} (build inputs)"] = len(rows)

    report = {"schema": "moonlit-lovers-image-occurrence-mirror/v1",
              "units_with_a_render": covered, "occurrences": summary,
              "new_build_inputs": added_to_build}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
