#!/usr/bin/env python3
"""Single reproducible Moonlit Lovers Korean WIP build entry point.

This script performs no translation generation and never calls a local/remote AI.
It only consumes translation/image assets already present in the project and wires
all proven technical stages together:

1. Verify the Japanese original ISO.
2. Extract/build the Moonlit embedded Korean font map/ELF.
3. Materialize translated SCENARIO leaves (with explicit WIP handling for the
   eight currently over-limit selection rows).
4. Rebuild SCENARIO.DAT and mirror IDX.DAT.
5. Install the patched SLPM_654.29 font ELF.
6. Patch the existing remaining-text overlay into PIDX/FSTS containers and verify
   it against the immutable Japanese ISO, excluding ADV blocks that are exact
   SCENARIO runtime copies.
7. Synchronize the translated SCENARIO raw blocks into those fixed-slot ADV
   runtime copies.
8. Patch GADAT030/031/032 translated images, including ADV runtime copies.
9. Re-verify scenario/IDX structure, font readback, every image primary/runtime
   stream, every remaining-overlay target, and ADV scenario runtime copies after
   all later stages.

The current remaining-text overlay is intentionally partial.  This therefore
produces a WIP integration ISO unless all remaining translations have been filled.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mmap
import shutil
import subprocess
import sys
from pathlib import Path

import eternal_lovers_patch_remaining as remaining_engine
import galaxy_angel_build as iso_builder
import galaxy_angel_patch_gadat032_images as image_patcher
import galaxy_angel_translation as translation
import ikusa_lz
import moonlit_lovers_build as mlbuild
import moonlit_lovers_font as mlfont
import moonlit_lovers_materialize_scenario as materializer
import moonlit_lovers_patch_adv_scenario_copies as adv_scenario_runtime
import moonlit_lovers_patch_remaining as remaining_adapter
import moonlit_lovers_resources as resources
import moonlit_lovers_sync_adv_image_fsts as adv_image_fsts
import moonlit_lovers_verify_structure as structure_verify


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "work/galaxy_angel_moonlit_lovers"
ASSETS = PROJECT / "assets"
BUILD = PROJECT / "build"
IMAGE_REFERENCE_OVERRIDES = ASSETS / "image_extraction/reference_overrides.json"
IMAGE_MANUAL_AUTHORITY = ASSETS / "image_extraction/manual_translated_png_authority.json"
IMAGE_QUALITY_FIX_REPORT = BUILD / "image_compare/quality_fix_report.json"
ORIGINAL_SHA256 = "990be804914335df22223c0070ec677ace4b5684f367dd9b04fa8ab55263a3fe"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str]) -> None:
    print("+", subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def verify_original(path: Path, allow_unverified: bool) -> str:
    digest = sha256(path)
    if digest != ORIGINAL_SHA256 and not allow_unverified:
        raise SystemExit(
            f"original ISO SHA-256 mismatch: {digest} != {ORIGINAL_SHA256}"
        )
    if digest != ORIGINAL_SHA256:
        print(
            f"WARNING: unverified original ISO {digest}; expected {ORIGINAL_SHA256}",
            flush=True,
        )
    else:
        print(f"original ISO verified: {digest}", flush=True)
    return digest


def extract_elf(iso_path: Path, output: Path) -> bytes:
    with iso_path.open("rb") as stream, mmap.mmap(
        stream.fileno(), 0, access=mmap.ACCESS_READ
    ) as image:
        files = iso_builder.iso_files(image)
        item = files["SLPM_654.29"]
        begin = item.extent * iso_builder.SECTOR
        data = bytes(image[begin:begin + item.size])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    print(
        f"extracted SLPM_654.29 size={len(data)} sha256={hashlib.sha256(data).hexdigest()}",
        flush=True,
    )
    return data


def install_elf_in_place(iso_path: Path, elf_path: Path) -> str:
    elf = elf_path.read_bytes()
    with iso_path.open("r+b") as stream, mmap.mmap(stream.fileno(), 0) as image:
        files = iso_builder.iso_files(image)
        item = files["SLPM_654.29"]
        if len(elf) != item.size:
            raise SystemExit(f"patched ELF size changed: {len(elf)} != {item.size}")
        begin = item.extent * iso_builder.SECTOR
        image[begin:begin + item.size] = elf
        image.flush()
    with iso_path.open("rb") as stream, mmap.mmap(
        stream.fileno(), 0, access=mmap.ACCESS_READ
    ) as image:
        item = iso_builder.iso_files(image)["SLPM_654.29"]
        begin = item.extent * iso_builder.SECTOR
        installed = bytes(image[begin:begin + item.size])
    if installed != elf:
        raise SystemExit("patched ELF readback mismatch")
    digest = hashlib.sha256(installed).hexdigest()
    print(f"installed SLPM_654.29 sha256={digest}", flush=True)
    return digest


def remaining_payload(
    index_path: Path,
    overlay_path: Path,
    reference_iso: Path,
    tbi_overlay: Path | None = None,
    tbi_manifest: Path | None = None,
    tbi_raw_root: Path | None = None,
) -> tuple[dict, set[int]]:
    excluded_adv_offsets = remaining_adapter.scenario_runtime_copy_offsets(
        reference_iso, PROJECT / "source/scenario"
    )
    payload = remaining_adapter.merge_overlay(
        remaining_adapter.load_json(index_path),
        remaining_adapter.load_json(overlay_path),
        excluded_adv_offsets,
    )
    if tbi_overlay is not None:
        if tbi_manifest is None or tbi_raw_root is None:
            raise SystemExit("TBI overlay requires manifest and raw root")
        tbi_payload = remaining_adapter.build_tbi_com_payload(
            tbi_overlay, tbi_manifest, tbi_raw_root
        )
        payload["candidates"].extend(tbi_payload["candidates"])
    return payload, excluded_adv_offsets


def verify_remaining_targets_only(
    reference_iso: Path,
    patched_iso: Path,
    payload: dict,
    encoding_map: Path,
) -> dict[str, dict]:
    custom_map = translation.load_custom_map(encoding_map)
    assert custom_map is not None
    targets = remaining_engine.collect_targets(payload)
    results: dict[str, dict] = {}
    with reference_iso.open("rb") as ref_stream, patched_iso.open("rb") as out_stream:
        with mmap.mmap(ref_stream.fileno(), 0, access=mmap.ACCESS_READ) as ref_image, mmap.mmap(
            out_stream.fileno(), 0, access=mmap.ACCESS_READ
        ) as out_image:
            ref_files = iso_builder.iso_files(ref_image)
            out_files = iso_builder.iso_files(out_image)
            for stem, blocks in sorted(targets.items()):
                ref_item = iso_builder.resolve_iso_file(ref_files, stem)
                out_item = iso_builder.resolve_iso_file(out_files, stem)
                ref_begin = ref_item.extent * iso_builder.SECTOR
                out_begin = out_item.extent * iso_builder.SECTOR
                ref_container = bytes(ref_image[ref_begin:ref_begin + ref_item.size])
                out_container = bytes(out_image[out_begin:out_begin + out_item.size])
                ref_map = remaining_engine.merged_resources(ref_container, stem)
                out_map = remaining_engine.merged_resources(out_container, stem)
                out_by_record = {
                    record: item
                    for item in out_map.values()
                    for record in item.record_positions
                }
                verified_resources = verified_strings = 0
                for offset, units in sorted(blocks.items()):
                    ref_resource = ref_map[offset]
                    record = ref_resource.record_positions[0]
                    out_resource = out_by_record.get(record)
                    if out_resource is None:
                        raise SystemExit(
                            f"remaining target missing after integration: {stem}:{offset:#x}"
                        )
                    ref_raw = resources.decompress_resource(
                        ref_container,
                        ref_resource.offset,
                        ref_resource.raw_size,
                        ref_resource.compressed_size,
                    )
                    expected, count = remaining_engine.rebuild_resource(
                        ref_raw, units, custom_map
                    )
                    actual = resources.decompress_resource(
                        out_container,
                        out_resource.offset,
                        out_resource.raw_size,
                        out_resource.compressed_size,
                    )
                    if actual != expected:
                        raise SystemExit(
                            f"remaining target changed after later stages: {stem}:{offset:#x}"
                        )
                    verified_resources += 1
                    verified_strings += count
                results[stem] = {
                    "verified_resources": verified_resources,
                    "verified_strings": verified_strings,
                }
    return results


def verify_image_reports(iso_path: Path, reports: list[Path]) -> dict:
    totals = {
        "images": 0,
        "primary_verified": 0,
        "runtime_copies_verified": 0,
        "quantized_images": 0,
    }
    with iso_path.open("rb") as stream, mmap.mmap(
        stream.fileno(), 0, access=mmap.ACCESS_READ
    ) as image:
        files = iso_builder.iso_files(image)
        for report_path in reports:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            stem = str(payload.get("primary_container") or "").upper()
            if not stem:
                raise SystemExit(f"image report missing primary_container: {report_path}")
            item = iso_builder.resolve_iso_file(files, stem)
            begin = item.extent * iso_builder.SECTOR
            for entry in payload.get("entries", []):
                totals["images"] += 1
                offset = int(entry["primary_offset"])
                raw, _used = ikusa_lz.decompress(image, begin + offset)
                digest = hashlib.sha256(raw).hexdigest()
                if digest != entry["raw_sha256"]:
                    raise SystemExit(
                        f"image primary readback mismatch: {stem}:{entry['name']}"
                    )
                totals["primary_verified"] += 1
                if entry.get("quantized_colours") is not None:
                    totals["quantized_images"] += 1
                for runtime in entry.get("runtime_copies", []):
                    runtime_raw, _runtime_used = ikusa_lz.decompress(
                        image, int(runtime["iso_offset"])
                    )
                    if hashlib.sha256(runtime_raw).hexdigest() != entry["raw_sha256"]:
                        raise SystemExit(
                            f"image runtime readback mismatch: "
                            f"{runtime['container']}:{entry['name']}"
                        )
                    totals["runtime_copies_verified"] += 1
    return totals


def verify_named_container_indexes(iso_path: Path, stems: list[str]) -> dict[str, dict]:
    results = {}
    with iso_path.open("rb") as stream, mmap.mmap(
        stream.fileno(), 0, access=mmap.ACCESS_READ
    ) as image:
        files = structure_verify.builder.iso_files(image)
        for stem in stems:
            result = structure_verify.verify_container(image, files, stem)
            structure_verify.report(result)
            if not result["complete"]:
                raise SystemExit(f"central IDX verification failed: {stem}")
            results[stem] = result
    return results


def _resolved_reference_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (ROOT / path).resolve()


def _manual_authority(container_name: str) -> set[str]:
    if not IMAGE_MANUAL_AUTHORITY.is_file():
        return set()
    payload = json.loads(IMAGE_MANUAL_AUTHORITY.read_text(encoding="utf-8"))
    images = payload.get("containers", {}).get(container_name, {}).get("images", [])
    return {str(name) for name in images}


def authoritative_image_state() -> dict[str, str]:
    """Hash the source/translated PNG trees that must stay byte-for-byte unchanged."""
    root = ASSETS / "image_extraction"
    result: dict[str, str] = {}
    for leaf in ("png", "translated_png"):
        for path in sorted(root.glob(f"*/japanese_images/{leaf}/*.png")):
            rel = path.relative_to(PROJECT).as_posix()
            result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def image_state_summary(state: dict[str, str]) -> dict[str, object]:
    digest = hashlib.sha256()
    for path, file_hash in sorted(state.items()):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return {"file_count": len(state), "aggregate_sha256": digest.hexdigest()}


def assert_authoritative_images_unchanged(
    baseline: dict[str, str], stage: str
) -> dict[str, object]:
    current = authoritative_image_state()
    missing = sorted(set(baseline) - set(current))
    added = sorted(set(current) - set(baseline))
    changed = sorted(
        path for path in set(baseline) & set(current) if baseline[path] != current[path]
    )
    report = {
        "schema": "moonlit-lovers-current-image-preservation/v1",
        "stage": stage,
        "baseline": image_state_summary(baseline),
        "current": image_state_summary(current),
        "missing": missing,
        "added": added,
        "changed": changed,
    }
    report_path = BUILD / "current_image_preservation_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if missing or added or changed:
        raise SystemExit(
            "authoritative image tree changed during preserve-current-images build: "
            f"stage={stage} missing={len(missing)} added={len(added)} changed={len(changed)}"
        )
    return report


def _reference_overrides(container_name: str) -> dict[str, tuple[dict, dict, dict]]:
    """Load exact-source image overrides backed by a verified reference build report."""
    if not IMAGE_REFERENCE_OVERRIDES.is_file():
        return {}
    payload = json.loads(IMAGE_REFERENCE_OVERRIDES.read_text(encoding="utf-8"))
    container = payload.get("containers", {}).get(container_name, {})
    images = container.get("images", {})
    if not images:
        return {}
    report_path = _resolved_reference_path(str(container["report"]))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    by_name = {str(row["name"]): row for row in report.get("entries", [])}
    result: dict[str, tuple[dict, dict, dict]] = {}
    for png, spec in images.items():
        resource_name = str(spec["resource_name"])
        row = by_name.get(resource_name)
        if row is None:
            raise SystemExit(
                f"reference image report is missing {container_name}:{resource_name}"
            )
        result[str(png)] = (spec, row, report)
    return result


def _materialize_verified_reference(
    container_name: str,
    source_png: Path,
    spec: dict,
    report_row: dict,
    report: dict,
) -> Path:
    """Read the localized TEX back from the reference project's verified final ISO.

    The mutable translated_png tree is deliberately not trusted: later image QA work may
    replace those PNGs after the final ISO report was produced.  The final ISO plus the
    report's expected readback pixel hash is the immutable authority here.
    """
    reference_iso = _resolved_reference_path(str(report["iso"]))
    if not reference_iso.is_file():
        raise SystemExit(f"reference final ISO is missing: {reference_iso}")
    output_dir = BUILD / "reference_image_overrides" / container_name
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / source_png.name
    with reference_iso.open("rb") as stream, mmap.mmap(
        stream.fileno(), 0, access=mmap.ACCESS_READ
    ) as image:
        files = iso_builder.iso_files(image)
        item = iso_builder.resolve_iso_file(files, container_name)
        begin = item.extent * iso_builder.SECTOR
        raw, _used = ikusa_lz.decompress(image, begin + int(report_row["primary_offset"]))
    decoded = image_patcher.decode_tex(raw).convert("RGBA")
    actual_hash = image_patcher.pixel_hash(decoded)
    expected_hash = str(report_row["expected_pixel_sha256"])
    if actual_hash != expected_hash:
        raise SystemExit(
            f"reference final ISO readback mismatch for {container_name}:{source_png.name}: "
            f"{actual_hash}!={expected_hash}"
        )
    decoded.save(output)
    return output


def _quality_fix_overrides(container_name: str) -> dict[str, Path]:
    if not IMAGE_QUALITY_FIX_REPORT.is_file():
        return {}
    payload = json.loads(IMAGE_QUALITY_FIX_REPORT.read_text(encoding="utf-8"))
    output_root = Path(str(payload["output_root"]))
    result: dict[str, Path] = {}
    for row in payload.get("items", []):
        if str(row.get("container")) != container_name:
            continue
        png = str(row["png"])
        path = output_root / container_name / png
        if not path.is_file():
            raise SystemExit(f"quality-fix PNG is missing: {path}")
        expected = str(row.get("sha256") or "")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected and actual != expected:
            raise SystemExit(
                f"quality-fix PNG changed after report: {container_name}:{png}: "
                f"{actual}!={expected}"
            )
        result[png] = path
    return result


def curated_png_args(
    container_dir: Path, preserve_current_images: bool = False
) -> list[str]:
    """Return current curated translations, with exact-source verified reference overrides.

    japanese_images/png remains the authority: deleting a source there always removes it
    from the build even if an override entry still exists.  A reference asset is accepted
    only when its Japanese source is pixel-identical to the current Moonlit source and the
    translated PNG is byte-for-pixel identical to the input recorded by the reference
    project's successful final image patch report.
    """
    originals = container_dir / "japanese_images/png"
    translated = container_dir / "japanese_images/translated_png"
    overrides = _reference_overrides(container_dir.name)
    quality_fixes = _quality_fix_overrides(container_dir.name)
    manual_authority = _manual_authority(container_dir.name)
    args: list[str] = []
    for source in sorted(originals.glob("*.png"), key=lambda p: p.name.lower()):
        target = translated / source.name
        if preserve_current_images:
            if not target.is_file():
                raise SystemExit(
                    f"preserve-current-images translated_png is missing: {target}"
                )
            print(
                f"preserved translated_png authority: {container_dir.name}:{source.name} -> {target}",
                flush=True,
            )
            args.extend(["--png", str(target)])
            continue
        if container_dir.name == "GADAT032" and target.is_file():
            print(
                f"existing translated_png authority: {container_dir.name}:{source.name} -> {target}",
                flush=True,
            )
            args.extend(["--png", str(target)])
            continue
        if source.name in manual_authority:
            if not target.is_file():
                raise SystemExit(f"manual-authority translated_png is missing: {target}")
            print(
                f"manual translated_png authority: {container_dir.name}:{source.name} -> {target}",
                flush=True,
            )
            args.extend(["--png", str(target)])
            continue
        override = overrides.get(source.name)
        quality_fix = quality_fixes.get(source.name)
        if override is None and quality_fix is None:
            target = translated / source.name
            if not target.is_file():
                raise SystemExit(f"curated image is missing translated_png: {target}")
        elif override is None:
            target = quality_fix
            print(
                f"quality-fix image override: {container_dir.name}:{source.name} -> {target}",
                flush=True,
            )
        else:
            spec, report_row, report = override
            mutable_translation = Path(str(report_row["png"]))
            reference_source = (
                mutable_translation.parent.parent / "png" / mutable_translation.name
            )
            if not reference_source.is_file():
                raise SystemExit(
                    f"reference Japanese source is missing for {container_dir.name}:{source.name}"
                )
            current_source_hash = image_patcher.image_hash(source)
            reference_source_hash = image_patcher.image_hash(reference_source)
            if current_source_hash != reference_source_hash:
                raise SystemExit(
                    f"reference Japanese source differs for {container_dir.name}:{source.name}: "
                    f"{current_source_hash}!={reference_source_hash}"
                )
            target = _materialize_verified_reference(
                container_dir.name, source, spec, report_row, report
            )
            print(
                f"reference final-ISO override: {container_dir.name}:{source.name} "
                f"-> {spec['resource_name']} ({target})",
                flush=True,
            )
        args.extend(["--png", str(target)])
    return args


def curated_png_list_args(
    container_dir: Path, preserve_current_images: bool = False
) -> list[str]:
    """Materialize the resolved PNG selection to a short UTF-8 list-file argument."""
    expanded = curated_png_args(container_dir, preserve_current_images)
    paths = expanded[1::2]
    list_path = BUILD / f"{container_dir.name.lower()}_image_inputs.txt"
    list_path.write_text("\n".join(paths) + ("\n" if paths else ""), encoding="utf-8")
    return ["--png-list", str(list_path)]


def image_commands(
    output_iso: Path,
    reports: list[Path],
    preserve_current_images: bool = False,
) -> list[list[str]]:
    patcher = ROOT / "tools/galaxy_angel_patch_gadat032_images.py"
    image_root = ASSETS / "image_extraction"
    full_root = ASSETS / "full_extraction"
    # Preserve mode freezes which PNG files are consumed and forbids regenerating them.
    # TEX palette conversion itself remains enabled because indexed4/indexed8 target formats
    # cannot represent arbitrary source RGBA byte-for-byte.
    preserve_flags: list[str] = []

    gadat030 = image_root / "GADAT030"
    report030 = BUILD / "gadat030_image_patch_report.json"
    reports.append(report030)
    cmd030 = [
        sys.executable, "-u", str(patcher),
        "--iso", str(output_iso),
        "--primary-container", "GADAT030",
        *preserve_flags,
        *curated_png_list_args(gadat030, preserve_current_images),
        "--runtime-container", "ADV",
        "--strict-name-data-container", "ADV",
        "--report", str(report030),
        "--cache-dir", str(BUILD / "image_cache_gadat030"),
    ]

    gadat031 = image_root / "GADAT031"
    report031 = BUILD / "gadat031_image_patch_report.json"
    reports.append(report031)
    cmd031 = [
        sys.executable, "-u", str(patcher),
        "--iso", str(output_iso),
        "--primary-container", "GADAT031",
        *preserve_flags,
        *curated_png_list_args(gadat031, preserve_current_images),
        "--image-manifest", str(gadat031 / "manifest.json"),
        "--resource-manifest", str(full_root / "GADAT031/manifest.json"),
        "--no-runtime-copies",
        "--report", str(report031),
        "--cache-dir", str(BUILD / "image_cache_gadat031"),
    ]

    gadat032 = image_root / "GADAT032"
    report032 = BUILD / "gadat032_image_patch_report.json"
    reports.append(report032)
    cmd032 = [
        sys.executable, "-u", str(patcher),
        "--iso", str(output_iso),
        "--primary-container", "GADAT032",
        *preserve_flags,
        *curated_png_list_args(gadat032, preserve_current_images),
        "--image-manifest", str(gadat032 / "japanese_images/render_report.json"),
        # The battle-UI audit added its own textures to this container, and they are described
        # by the renderer's manifest rather than by the earlier render report.
        "--image-manifest", str(gadat032 / "japanese_images/manifest.json"),
        "--resource-manifest", str(full_root / "GADAT032/manifest.json"),
        "--runtime-container", "ADV",
        "--report", str(report032),
        "--cache-dir", str(BUILD / "image_cache_gadat032"),
    ]

    # SLG carries the battle UI.  Nothing in this container had been translated, so it had no
    # patch stage at all and every battle button stayed Japanese in game.
    slg = image_root / "SLG"
    report_slg = BUILD / "slg_image_patch_report.json"
    reports.append(report_slg)
    cmd_slg = [
        sys.executable, "-u", str(patcher),
        "--iso", str(output_iso),
        "--primary-container", "SLG",
        *preserve_flags,
        *curated_png_list_args(slg, preserve_current_images),
        "--image-manifest", str(slg / "japanese_images/manifest.json"),
        "--resource-manifest", str(full_root / "SLG/manifest.json"),
        "--runtime-container", "ADV",
        "--report", str(report_slg),
        "--cache-dir", str(BUILD / "image_cache_slg"),
    ]
    return [cmd030, cmd031, cmd032, cmd_slg]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-iso", type=Path, required=True)
    parser.add_argument(
        "--output-iso",
        type=Path,
        default=BUILD / "Galaxy_Angel_Moonlit_Lovers_KO_wip.iso",
    )
    parser.add_argument("--allow-unverified-original", action="store_true")
    parser.add_argument(
        "--wip-keep-selection-overflow-original",
        action="store_true",
        help=(
            "Keep currently over-34-byte selection translations in Japanese so the "
            "technical WIP integration build can proceed. Final builds should omit "
            "this flag and resolve those translations first."
        ),
    )
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Debug only: skip all translated image insertion.",
    )
    parser.add_argument(
        "--preserve-current-images",
        action="store_true",
        help=(
            "Use only the current japanese_images/translated_png files, skip all image "
            "render/regeneration/override paths, forbid redraw/refit fallbacks, and verify "
            "the source/translated PNG trees remain byte-for-byte unchanged. Target TEX "
            "palette conversion is still allowed when required by the original format."
        ),
    )
    args = parser.parse_args()

    original_iso = args.original_iso.resolve()
    output_iso = args.output_iso.resolve()
    BUILD.mkdir(parents=True, exist_ok=True)
    original_digest = verify_original(original_iso, args.allow_unverified_original)
    image_baseline = authoritative_image_state() if args.preserve_current_images else None
    if image_baseline is not None:
        baseline_report = {
            "schema": "moonlit-lovers-current-image-baseline/v1",
            **image_state_summary(image_baseline),
            "files": image_baseline,
        }
        (BUILD / "current_image_baseline.json").write_text(
            json.dumps(baseline_report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            "preserve-current-images baseline: "
            f"{baseline_report['file_count']} PNGs "
            f"aggregate={baseline_report['aggregate_sha256']}",
            flush=True,
        )

    translation_assets = ASSETS / "translation"
    remaining_index = translation_assets / "remaining/remaining_candidates.json"
    remaining_overlay = translation_assets / "remaining/remaining_translations.json"
    tbi_overlay = translation_assets / "remaining/tbi_com_translations.json"
    tbi_manifest = ASSETS / "full_extraction/SCENARIO/manifest.json"
    tbi_raw_root = ASSETS / "full_extraction/SCENARIO/raw/dat/scenario"
    original_elf = BUILD / "SLPM_654.29.original"
    font_elf = BUILD / "SLPM_654.29.font_wip"
    font_map = BUILD / "font_map.json"
    scenario_out = BUILD / "scenario_materialized"
    scenario_report = BUILD / "scenario_materialize_report.json"
    remaining_report = BUILD / "remaining_patch_report.json"
    tbi_report = BUILD / "tbi_com_patch_report.json"
    adv_scenario_report = BUILD / "adv_scenario_runtime_patch_report.json"
    integrated_report = BUILD / "integrated_build_report.json"

    extract_elf(original_iso, original_elf)
    mlfont.build_font(
        [translation_assets, remaining_overlay, tbi_overlay],
        original_elf,
        font_elf,
        font_map,
        ROOT
        / "vendor/pretendard/packages/pretendard/dist/public/static/alternative/Pretendard-Bold.ttf",
        20,
        0,
        hangul_horizontal_scale=1.0,
    )

    if scenario_out.exists():
        shutil.rmtree(scenario_out)
    materialize_report = materializer.materialize(
        PROJECT / "source/scenario",
        translation_assets,
        scenario_out,
        font_map,
        scenario_report,
        34,
        args.wip_keep_selection_overflow_original,
    )
    if materialize_report["selection_overflow_count"]:
        if not args.wip_keep_selection_overflow_original:
            raise SystemExit("selection overflow rows remain; WIP override was not enabled")
        print(
            "WARNING: WIP build keeps "
            f"{materialize_report['selection_overflow_count']} over-limit selections Japanese",
            flush=True,
        )

    # TBI room-description strings live in separate SCENARIO PIDX leaves.  Patch
    # those leaves while SCENARIO.DAT still has its pristine, bounded ISO size.
    # After the translated scenario build, oversized dialogue leaves may point to
    # a backing copy near the end of the disc and SCENARIO.DAT's logical ISO size
    # consequently spans unrelated files.  Repacking SCENARIO at that point would
    # overwrite those overlapping files (notably SLG.DAT).
    base_payload, excluded_adv_offsets = remaining_payload(
        remaining_index,
        remaining_overlay,
        original_iso,
    )
    base_targets = remaining_engine.collect_targets(base_payload)
    if "SCENARIO" in base_targets:
        raise SystemExit(
            "non-TBI remaining translations unexpectedly target SCENARIO; "
            "they must be applied before the scenario backing-copy build"
        )
    tbi_payload = remaining_adapter.build_tbi_com_payload(
        tbi_overlay, tbi_manifest, tbi_raw_root
    )
    payload = {
        "candidates": [
            *base_payload["candidates"],
            *tbi_payload["candidates"],
        ]
    }
    target_summary = {
        stem: {
            "resources": len(blocks),
            "occurrences": sum(len(items) for items in blocks.values()),
        }
        for stem, blocks in sorted(remaining_engine.collect_targets(payload).items())
    }

    if tbi_payload["candidates"]:
        run([
            sys.executable,
            "-u",
            str(ROOT / "tools/moonlit_lovers_patch_remaining.py"),
            "--iso",
            str(original_iso),
            "--output-iso",
            str(output_iso),
            "--index",
            str(remaining_index),
            "--overlay",
            str(remaining_overlay),
            "--tbi-overlay",
            str(tbi_overlay),
            "--tbi-manifest",
            str(tbi_manifest),
            "--tbi-raw-root",
            str(tbi_raw_root),
            "--encoding-map",
            str(font_map),
            "--report",
            str(tbi_report),
            "--cache-dir",
            str(BUILD / "remaining_compressed_cache"),
            "--container",
            "SCENARIO",
        ])
    else:
        shutil.copyfile(original_iso, output_iso)

    mlbuild.build(
        original_iso,
        output_iso,
        PROJECT / "source/scenario",
        scenario_out,
        ROOT / "tools/ikusa_lz.py",
        ["SCENARIO"],
        force_recompress=False,
        patch_existing=True,
    )
    elf_digest = install_elf_in_place(output_iso, font_elf)

    # The full remaining-text set can make SLG exceed its fixed ISO allocation.
    # Keep the runtime-visible container at its original LBA and move only its
    # overflow into a reserved, addressable region.
    backing_region = BUILD / "backing_region.json"
    run([
        sys.executable,
        "-u",
        str(ROOT / "tools/eternal_lovers_reserve_backing_region.py"),
        "--iso",
        str(output_iso),
        "--for",
        "SLG",
        "--for",
        "SLGSTAGE",
        "--region",
        str(backing_region),
    ])

    if base_payload["candidates"]:
        run([
            sys.executable,
            "-u",
            str(ROOT / "tools/moonlit_lovers_patch_remaining.py"),
            "--iso",
            str(output_iso),
            "--verify-source-iso",
            str(original_iso),
            "--index",
            str(remaining_index),
            "--overlay",
            str(remaining_overlay),
            "--encoding-map",
            str(font_map),
            "--report",
            str(remaining_report),
            "--cache-dir",
            str(BUILD / "remaining_compressed_cache"),
            "--backing-region",
            str(backing_region),
            "--source-scenario",
            str(PROJECT / "source/scenario"),
        ])

    run([
        sys.executable,
        "-u",
        str(ROOT / "tools/moonlit_lovers_patch_adv_scenario_copies.py"),
        "--iso",
        str(output_iso),
        "--original-iso",
        str(original_iso),
        "--source-scenario",
        str(PROJECT / "source/scenario"),
        "--built-scenario",
        str(scenario_out),
        "--report",
        str(adv_scenario_report),
    ])

    image_reports: list[Path] = []
    image_preservation: dict[str, object] = {}
    adv_image_fsts_report = BUILD / "adv_image_fsts_sync_report.json"
    if not args.skip_images:
        if args.preserve_current_images:
            print(
                "preserve-current-images: skipping all image renderers, quality-fix outputs, "
                "and reference overrides; current translated_png is the only authority",
                flush=True,
            )
        else:
            # Normal reproducible mode regenerates the derived image inputs before insertion.
            run([
                sys.executable, "-u",
                str(ROOT / "tools/eternal_lovers_render_haplc.py"),
                "--project", str(PROJECT),
                "--layout", "moonlit",
                "--translations", str(BUILD / "haplc_wording_from_gaplc.json"),
                "--never-overwrite",
            ])
            run([
                sys.executable, "-u",
                str(ROOT / "tools/eternal_lovers_render_candidate_images.py"),
                "--project", str(PROJECT),
                "--layout", "moonlit",
                "--never-overwrite",
            ])
            run([
                sys.executable,
                "-u",
                str(ROOT / "tools/moonlit_lovers_render_album_titles.py"),
                "--project",
                str(PROJECT),
            ])
            run([
                sys.executable,
                "-u",
                str(ROOT / "tools/moonlit_lovers_render_quality_fixes.py"),
                "--output-root",
                str(BUILD / "image_quality_fixes"),
                "--report",
                str(IMAGE_QUALITY_FIX_REPORT),
            ])

        mirror_command = [
            sys.executable, "-u",
            str(ROOT / "tools/moonlit_lovers_mirror_image_occurrences.py"),
            "--project", str(PROJECT),
            "--container", "SLG",
            "--container", "SLGRES",
            "--container", "SLGSTAGE",
            "--container", "ADV",
            # SLG is PIDX-indexed: its extra copies join that container's own build inputs,
            # because writing them through an FSTS record overwrites the PIDX tree.
            "--pidx-container", "SLG",
            "--targets", str(BUILD / "missing_translation_images_20260903.json"),
            "--targets-only-container", "ADV",
            "--report", str(BUILD / "image_occurrence_mirror_report.json"),
        ]
        if args.preserve_current_images:
            mirror_command.append("--preserve-existing-image-tree")
        run(mirror_command)
        if image_baseline is not None:
            image_preservation = assert_authoritative_images_unchanged(
                image_baseline, "after-mirror"
            )

        for command in image_commands(
            output_iso, image_reports, args.preserve_current_images
        ):
            run(command)
        if image_baseline is not None:
            image_preservation = assert_authoritative_images_unchanged(
                image_baseline, "after-primary-image-patches"
            )

        adv_image_fsts.sync(output_iso, image_reports, adv_image_fsts_report)
        # Every battle texture is stored again inside each per-stage bank, and those banks are
        # FSTS-indexed, which the PIDX image patcher cannot address.  Patching only the named
        # copy leaves the Japanese one on screen during a battle, so each copy is written
        # through its own bank record here, after the passes that repack those banks.
        battle_command = [
            sys.executable, "-u",
            str(ROOT / "tools/eternal_lovers_patch_battle_bank_images.py"),
            "--iso", str(output_iso),
            "--project", str(PROJECT),
            "--layout", "moonlit",
            "--container", "SLGRES",
            "--container", "SLGSTAGE",
            "--container", "ADV",
            "--report", str(BUILD / "battle_bank_images_report.json"),
        ]
        if args.preserve_current_images:
            battle_command.append("--no-refit")
        run(battle_command)
        if image_baseline is not None:
            image_preservation = assert_authoritative_images_unchanged(
                image_baseline, "after-battle-bank-patches"
            )

    speaker_report = BUILD / "speaker_name_patch_report.json"
    run([
        sys.executable,
        "-u",
        str(ROOT / "tools/moonlit_lovers_speakers.py"),
        "--iso",
        str(output_iso),
        "--names",
        str(translation_assets / "speaker_names.json"),
        "--encoding-map",
        str(font_map),
        "--report",
        str(speaker_report),
    ])

    index_verification = verify_named_container_indexes(
        output_iso,
        ["SCENARIO", "SLG", "GADAT000", "GADAT030", "GADAT031", "GADAT032"],
    )

    with output_iso.open("rb") as stream, mmap.mmap(
        stream.fileno(), 0, access=mmap.ACCESS_READ
    ) as image:
        item = iso_builder.iso_files(image)["SLPM_654.29"]
        begin = item.extent * iso_builder.SECTOR
        installed_elf = bytes(image[begin:begin + item.size])
    if installed_elf != font_elf.read_bytes():
        raise SystemExit("final integrated ISO lost patched font ELF")

    remaining_final = (
        verify_remaining_targets_only(original_iso, output_iso, payload, font_map)
        if payload["candidates"]
        else {}
    )
    image_final = (
        verify_image_reports(output_iso, image_reports) if image_reports else {}
    )
    if image_baseline is not None:
        image_preservation = assert_authoritative_images_unchanged(
            image_baseline, "final"
        )

    final_digest = sha256(output_iso)
    report = {
        "schema": "moonlit-lovers-integrated-build/v1",
        "original_iso": str(original_iso),
        "original_sha256": original_digest,
        "output_iso": str(output_iso),
        "output_sha256": final_digest,
        "output_size": output_iso.stat().st_size,
        "font_elf_sha256": elf_digest,
        "font_custom_glyphs": len(
            json.loads(font_map.read_text(encoding="utf-8"))["characters"]
        ),
        "scenario": materialize_report,
        "remaining_overlay_entries": len(payload["candidates"]),
        "remaining_targets": target_summary,
        "remaining_excluded_adv_scenario_offsets": sorted(excluded_adv_offsets),
        "remaining_final_verification": remaining_final,
        "tbi_prepatch": (
            json.loads(tbi_report.read_text(encoding="utf-8"))
            if tbi_report.is_file()
            else {}
        ),
        "remaining_patch": (
            json.loads(remaining_report.read_text(encoding="utf-8"))
            if remaining_report.is_file()
            else {}
        ),
        "adv_scenario_runtime": json.loads(
            adv_scenario_report.read_text(encoding="utf-8")
        ),
        "speaker_names": json.loads(speaker_report.read_text(encoding="utf-8")),
        "images": image_final,
        "image_input_policy": (
            "current-translated-png-authority"
            if args.preserve_current_images
            else "normal-curated-build"
        ),
        "authoritative_image_preservation": image_preservation,
        "image_quality_fixes": (
            {}
            if args.preserve_current_images
            else (
                json.loads(IMAGE_QUALITY_FIX_REPORT.read_text(encoding="utf-8"))
                if IMAGE_QUALITY_FIX_REPORT.is_file()
                else {}
            )
        ),
        "image_reference_overrides": (
            {}
            if args.preserve_current_images
            else (
                json.loads(IMAGE_REFERENCE_OVERRIDES.read_text(encoding="utf-8"))
                if IMAGE_REFERENCE_OVERRIDES.is_file()
                else {}
            )
        ),
        "adv_image_fsts_sync": (
            json.loads(adv_image_fsts_report.read_text(encoding="utf-8"))
            if adv_image_fsts_report.is_file()
            else {}
        ),
        "named_container_index_verification": index_verification,
        "wip_selection_overflow_original": bool(
            materialize_report["selection_overflow_count"]
        ),
    }
    integrated_report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"BUILD OK {output_iso} size={output_iso.stat().st_size} sha256={final_digest}",
        flush=True,
    )
    print(f"report: {integrated_report}", flush=True)


if __name__ == "__main__":
    main()
