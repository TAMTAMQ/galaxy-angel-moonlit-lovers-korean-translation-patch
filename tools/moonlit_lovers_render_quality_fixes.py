#!/usr/bin/env python3
"""Render only currently confirmed Moonlit Lovers image QA fixes into build/.

This never writes japanese_images/png or translated_png.  The authoritative source
set remains the user's japanese_images/png directory.  Exact-source reference
images listed in reference_overrides.json are excluded because the final build
uses the already verified Eternal Lovers translations for those resources.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import moonlit_lovers_rework_missing_strict as strict

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "work/galaxy_angel_moonlit_lovers"
DEFAULT_OUTPUT = PROJECT / "build/image_quality_fixes"
DEFAULT_REPORT = PROJECT / "build/image_compare/quality_fix_report.json"
MANUAL_AUTHORITY = PROJECT / "assets/image_extraction/manual_translated_png_authority.json"

# These were rechecked one-by-one with the actual-glyph verifier after the broad
# visual audit.  No Japanese glyph pixels remain, and the corresponding audit
# lines contained no independent size/style/background complaint.
FALSE_JP_ONLY = {
    ("GADAT032", "block_002f3800.png"),
    ("GADAT032", "block_00387000.png"),
    ("GADAT032", "block_00c95000.png"),
    ("GADAT032", "block_00ca9800.png"),
}

# Album-title textures are owned by moonlit_lovers_repair_transparency_geometry.py.
# Their source Japanese rows are 36-45 px tall; the generic strict-quality crop
# can clip the corrected Korean geometry back down to roughly half height.
SOURCE_GEOMETRY_OWNED = {
    ("GADAT032", "block_009fd800.png"),
    ("GADAT032", "block_00a02800.png"),
    ("GADAT032", "block_00a06800.png"),
    ("GADAT032", "block_00a0b800.png"),
    ("GADAT032", "block_00a0f000.png"),
    ("GADAT032", "block_00a12000.png"),
    ("GADAT032", "block_00a16800.png"),
    ("GADAT032", "block_00a1a000.png"),
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def current_authority() -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    root = PROJECT / "assets/image_extraction"
    for container in ("GADAT030", "GADAT031", "GADAT032"):
        source = root / container / "japanese_images/png"
        if source.is_dir():
            result.update((container, path.name) for path in source.glob("*.png"))
    return result


def strict_issues() -> set[tuple[str, str]]:
    names: set[str] = set()
    for path in sorted((PROJECT / "analysis").glob("strict_quality_qwen38_*.json")):
        for result in load_json(path).get("results", []):
            for issue in result.get("issues", []):
                if issue.get("png"):
                    names.add(str(issue["png"]))
    authority = current_authority()
    by_name = {name: (container, name) for container, name in authority}
    return {by_name[name] for name in names if name in by_name}


def manual_authority() -> set[tuple[str, str]]:
    if not MANUAL_AUTHORITY.is_file():
        return set()
    payload = load_json(MANUAL_AUTHORITY)
    result: set[tuple[str, str]] = set()
    for container, data in payload.get("containers", {}).items():
        for png in data.get("images", []):
            result.add((str(container), str(png)))
    return result


def existing_translated_png() -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    base = PROJECT / "assets/image_extraction/GADAT032/japanese_images/translated_png"
    if base.is_dir():
        result.update(("GADAT032", path.name) for path in base.glob("*.png"))
    return result


def reference_overrides() -> set[tuple[str, str]]:
    path = PROJECT / "assets/image_extraction/reference_overrides.json"
    if not path.is_file():
        return set()
    payload = load_json(path)
    result: set[tuple[str, str]] = set()
    for container, data in payload.get("containers", {}).items():
        for png in data.get("images", {}):
            result.add((str(container), str(png)))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    authority = current_authority()
    targets = (
        (strict_issues() & authority)
        - reference_overrides()
        - manual_authority()
        - existing_translated_png()
        - FALSE_JP_ONLY
        - SOURCE_GEOMETRY_OWNED
    )
    output_root = args.output_root.resolve()
    qa = strict.rework_gadat030(targets, output_root) + strict.rework_gadat032(
        targets, output_root
    )
    generated = {(str(row["container"]), str(row["png"])) for row in qa}
    missing = sorted(targets - generated)
    if missing:
        raise SystemExit(f"quality-fix renderer did not generate all targets: {missing}")
    outside_changed = sum(
        int(row["outside_approved_text_region_changed_pixels"]) for row in qa
    )
    if outside_changed:
        raise SystemExit(f"quality-fix renderer changed protected pixels: {outside_changed}")

    payload = {
        "schema": "moonlit-image-quality-fix/v1",
        "authority": "assets/image_extraction/*/japanese_images/png",
        "output_root": str(output_root),
        "target_count": len(targets),
        "generated": len(qa),
        "GADAT030": sum(row["container"] == "GADAT030" for row in qa),
        "GADAT032": sum(row["container"] == "GADAT032" for row in qa),
        "reference_overrides_excluded": len(reference_overrides() & strict_issues()),
        "manual_translated_png_excluded": sorted(
            {
                f"{container}/{png}"
                for container, png in manual_authority()
                if (container, png) in authority and (container, png) in strict_issues()
            }
        ),
        "existing_gadat032_translated_png_excluded_count": len(
            existing_translated_png() & authority & strict_issues()
        ),
        "false_japanese_only_excluded": sorted(
            {f"{container}/{png}" for container, png in FALSE_JP_ONLY if (container, png) in authority}
        ),
        "source_geometry_owned_excluded": sorted(
            {
                f"{container}/{png}"
                for container, png in SOURCE_GEOMETRY_OWNED
                if (container, png) in authority and (container, png) in strict_issues()
            }
        ),
        "outside_approved_text_region_changed_pixels": outside_changed,
        "targets": [
            {"container": container, "png": png}
            for container, png in sorted(targets)
        ],
        "items": qa,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
