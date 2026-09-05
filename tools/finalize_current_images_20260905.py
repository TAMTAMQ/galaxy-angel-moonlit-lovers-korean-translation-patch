#!/usr/bin/env python3
"""Consolidate final evidence for the 2026-09-05 current-image Moonlit build."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from moonlit_lovers_apply_speaker_patch import root_files
from verify_font_speaker_fix_20260905 import verify_runtime

PROJECT = Path(__file__).resolve().parents[1]
BUILD = PROJECT / "build"
EXPECTED_ORIGINAL_SHA256 = "990be804914335df22223c0070ec677ace4b5684f367dd9b04fa8ab55263a3fe"
EXPECTED_SPEAKER_RAW_SHA256 = "bf76016dfae4f952e4340f98a2d0471bef85894138a79411e5a367235611410f"
EXPECTED_FONT_SHA256 = "3c170d8375f803ed70745565de22f26c8cd045887af90398146cf2e364bb94f9"
EXPECTED_STRICT = {
    "ADV": 2395,
    "GADAT000": 36,
    "GADAT030": 508,
    "GADAT031": 577,
    "GADAT032": 1930,
    "SCENARIO": 177,
    "SLG": 4102,
    "SLGRES": 2677,
    "SLGSTAGE": 9993,
}
EXPECTED_INDEXES = {
    "SCENARIO": (177, 61),
    "SLG": (4102, 116),
    "GADAT000": (36, 9),
    "GADAT030": (508, 22),
    "GADAT031": (577, 35),
    "GADAT032": (1930, 48),
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def file_hashes(path: Path) -> dict[str, str | int]:
    hs = {name: hashlib.new(name) for name in ("md5", "sha1", "sha256")}
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            for digest in hs.values():
                digest.update(chunk)
    return {"size": path.stat().st_size, **{name: digest.hexdigest() for name, digest in hs.items()}}


def basename(value: str) -> str:
    return value.replace("\\", "/").rsplit("/", 1)[-1]


def region_sha256(path: Path, offset: int, size: int) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        stream.seek(offset)
        remaining = size
        while remaining:
            chunk = stream.read(min(8 * 1024 * 1024, remaining))
            if not chunk:
                raise RuntimeError(f"short read: {path} offset={offset} size={size}")
            digest.update(chunk)
            remaining -= len(chunk)
    return digest.hexdigest()


def compare_stable_regions(base_iso: Path, final_iso: Path) -> dict:
    before = root_files(base_iso)
    after = root_files(final_iso)
    if set(before) != set(after):
        raise RuntimeError("root ISO file inventory changed")
    layout_mismatches = {
        name: {"base": before[name], "final": after[name]}
        for name in before
        if before[name] != after[name]
    }
    if layout_mismatches:
        raise RuntimeError(f"root ISO file layout changed: {layout_mismatches}")

    # Image reinsertion is allowed to change ADV/GADAT030/GADAT032/SLG/SLGRES/
    # SLGSTAGE and the central IDX mirror.  Everything below should remain the
    # corrected 2026-09-05 font/text/speaker build byte-for-byte identical.
    stable_files = [
        "SLPM_654.29;1",
        "GADAT000.DAT;1",
        "GADAT031.DAT;1",
        "GAML.DAT;1",
        "SE.DAT;1",
        "SLGEFF.DAT;1",
        "SVOICE.DAT;1",
        "SYSTEM.CNF;1",
    ]
    rows = {}
    for name in stable_files:
        offset, size = before[name]
        old = region_sha256(base_iso, offset, size)
        new = region_sha256(final_iso, offset, size)
        rows[name] = {"offset": offset, "size": size, "base_sha256": old, "final_sha256": new, "equal": old == new}
        if old != new:
            raise RuntimeError(f"unexpected change in stable root file: {name}")

    # SCENARIO's ISO directory size deliberately spans the backing region.  Hash
    # only its physical container through the next root-file extent (SE.DAT).
    scenario_offset = before["SCENARIO.DAT;1"][0]
    next_offset = min(offset for name, (offset, _size) in before.items() if offset > scenario_offset)
    scenario_size = next_offset - scenario_offset
    old = region_sha256(base_iso, scenario_offset, scenario_size)
    new = region_sha256(final_iso, scenario_offset, scenario_size)
    rows["SCENARIO.DAT;1:physical"] = {
        "offset": scenario_offset,
        "size": scenario_size,
        "base_sha256": old,
        "final_sha256": new,
        "equal": old == new,
    }
    if old != new:
        raise RuntimeError("SCENARIO physical container changed relative to corrected base")
    return {"layout_equal": True, "regions": rows, "ok": True}


def verify_stage_reports(final_iso: Path) -> dict:
    final_name = final_iso.name
    checks: list[dict[str, object]] = []

    def check(name: str, value: bool) -> None:
        checks.append({"name": name, "ok": bool(value)})

    scenario = load(BUILD / "scenario_materialize_report.json")
    check("scenario.dialogue", scenario.get("applied_dialogue_units") == 25510)
    check("scenario.selections", scenario.get("selection_translations") == 286)
    check("scenario.selection_overflow", scenario.get("selection_overflow_count") == 0)
    check("scenario.save_labels", scenario.get("save_label_translation_patterns_applied") == 446)
    check("scenario.mission_layout", scenario.get("mission_layout_override_patterns_applied") == 12)

    tbi = load(BUILD / "tbi_com_patch_report.json")
    tc = tbi["containers"]["SCENARIO"]
    tv = tbi["verification"]["SCENARIO"]
    check("tbi.target", basename(tbi["patched_iso"]) == final_name)
    check("tbi.resources", tc["applied_resources"] == 25 and tv["verified_resources"] == 25)
    check("tbi.strings", tc["applied_strings"] == 739 and tv["verified_strings"] == 739)
    check("tbi.overflows", tc["overflows"] == [])

    remaining = load(BUILD / "remaining_patch_report.json")
    expected_remaining = {
        "ADV": (1, 13),
        "GADAT000": (2, 26),
        "SLG": (281, 81223),
        "SLGRES": (81, 1994),
        "SLGSTAGE": (715, 192782),
    }
    check("remaining.target", basename(remaining["patched_iso"]) == final_name)
    remaining_summary = {}
    for stem, (resource_count, string_count) in expected_remaining.items():
        row = remaining["containers"][stem]
        verify = remaining["verification"][stem]
        good = (
            row["applied_resources"] == resource_count
            and row["applied_strings"] == string_count
            and row["overflows"] == []
            and verify["verified_resources"] == resource_count
            and verify["verified_strings"] == string_count
        )
        check(f"remaining.{stem}", good)
        remaining_summary[stem] = {"resources": resource_count, "strings": string_count, "ok": good}

    adv = load(BUILD / "adv_scenario_runtime_patch_report.json")
    check("adv_scenario.target", basename(adv["output_iso"]) == final_name)
    check("adv_scenario.runtime", adv["runtime_copies"] == 36 and adv["verification"]["verified_runtime_copies"] == 36)
    check("adv_scenario.fixed_slots", adv["relocated"] == 0 and adv["verification"]["unchanged_outside_allowed_regions"] is True)
    check("adv_scenario.resource_count", adv["verification"]["resource_count_after"] == 2395)

    expected_images = {
        "gadat030_image_patch_report.json": 134,
        "gadat031_image_patch_report.json": 0,
        "gadat032_image_patch_report.json": 398,
        "slg_image_patch_report.json": 165,
    }
    image_summary = {}
    for filename, count in expected_images.items():
        row = load(BUILD / filename)
        good = basename(row["iso"]) == final_name and row["changed_count"] == count
        check(f"images.{filename}", good)
        image_summary[filename] = {"changed_count": row["changed_count"], "ok": good}

    sync = load(BUILD / "adv_image_fsts_sync_report.json")
    check("adv_image_sync.target", basename(sync["iso"]) == final_name)
    check("adv_image_sync.runtime", sync["runtime_unique_offsets"] == 481 and sync["matched_fsts_resources"] == 481)
    check("adv_image_sync.strict", sync["strict_adv_resources_verified"] == 2395)

    battle = load(BUILD / "battle_bank_images_report.json")
    battle_summary = {}
    for stem, count in {"SLGRES": 295, "SLGSTAGE": 672, "ADV": 2}.items():
        row = battle["containers"][stem]
        good = row["targets"] == count and row["written"] == count and row["redrawn_smaller_to_fit"] == 0 and row["skipped"] == []
        check(f"battle.{stem}", good)
        battle_summary[stem] = {"targets": count, "written": row["written"], "ok": good}

    speaker = load(BUILD / "speaker_name_patch_report.json")
    check("speaker.target", basename(speaker["output_iso"]) == final_name)
    check("speaker.names", speaker["speaker_names_patched"] == 48)
    check("speaker.raw_hash", speaker["patched_raw_sha256"] == EXPECTED_SPEAKER_RAW_SHA256)
    check("speaker.readback", len(speaker["verified"]) == 3)
    canonical = speaker["canonical"]
    check("speaker.idx", canonical["idx_tuple_after"] == [98304, 902, 653] and canonical["idx_records_patched"] == 1)

    preservation = load(BUILD / "current_image_preservation_report.json")
    check("image_preservation.stage", preservation["stage"] == "after-battle-bank-patches")
    check("image_preservation.clean", preservation["missing"] == [] and preservation["added"] == [] and preservation["changed"] == [])

    return {
        "checks": checks,
        "remaining": remaining_summary,
        "images": image_summary,
        "battle": battle_summary,
        "ok": all(bool(row["ok"]) for row in checks),
    }


def verify_saved_evidence() -> dict:
    baseline = load(BUILD / "current_images_baseline_verify_20260905.json")
    images = load(BUILD / "current_images_readback_verify_20260905.json")
    indexes = load(BUILD / "current_images_indexes_verify_20260905.json")
    strict = {}
    for filename in (
        "current_images_strict_core_verify_20260905.json",
        "current_images_strict_slg_verify_20260905.json",
        "current_images_strict_slgstage_verify_20260905.json",
    ):
        strict.update(load(BUILD / filename))

    baseline_ok = (
        baseline.get("file_count") == 1403
        and baseline.get("missing") == []
        and baseline.get("added") == []
        and baseline.get("changed") == []
    )
    image_ok = images.get("images") == 697 and images.get("primary_verified") == 697 and images.get("runtime_copies_verified") == 481

    strict_ok = set(strict) == set(EXPECTED_STRICT)
    strict_rows = {}
    for stem, expected in EXPECTED_STRICT.items():
        row = strict.get(stem, {})
        good = row.get("resources") == expected and row.get("strict_decompress_verified") == expected
        strict_rows[stem] = {"expected": expected, "actual": row.get("strict_decompress_verified"), "ok": good}
        strict_ok = strict_ok and good

    index_ok = set(indexes) == set(EXPECTED_INDEXES)
    index_rows = {}
    for stem, (leaves, file_id) in EXPECTED_INDEXES.items():
        row = indexes.get(stem, {})
        good = row.get("complete") is True and row.get("pidx_leaves") == leaves and row.get("idx_matches") == leaves and row.get("file_id") == file_id and row.get("ambiguous_file_id") is False
        index_rows[stem] = {"expected_leaves": leaves, "file_id": file_id, "ok": good}
        index_ok = index_ok and good

    return {
        "baseline": baseline,
        "image_readback": images,
        "strict": strict_rows,
        "indexes": index_rows,
        "ok": baseline_ok and image_ok and strict_ok and index_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--base-fixed", type=Path, required=True)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    for path in (args.iso, args.base_fixed, args.original):
        if not path.is_file():
            raise SystemExit(f"missing input: {path}")

    final_hashes = file_hashes(args.iso)
    original_hashes = file_hashes(args.original)
    original_ok = original_hashes["sha256"] == EXPECTED_ORIGINAL_SHA256
    if not original_ok:
        raise SystemExit("original ISO hash mismatch")

    runtime = verify_runtime(
        args.iso,
        BUILD / "SLPM_654.29.font_wip",
        PROJECT / "assets/translation/speaker_names.json",
        BUILD / "speaker_name_patch_report.json",
    )
    runtime_ok = runtime["embedded_font_sha256"] == EXPECTED_FONT_SHA256 and runtime["speaker_raw_sha256"] == EXPECTED_SPEAKER_RAW_SHA256 and runtime["speaker_readback"] == "3/3"

    stable = compare_stable_regions(args.base_fixed, args.iso)
    stages = verify_stage_reports(args.iso)
    evidence = verify_saved_evidence()

    ok = original_ok and runtime_ok and stable["ok"] and stages["ok"] and evidence["ok"]
    payload = {
        "schema": "moonlit-lovers-current-images-final-verify/v1",
        "final_iso": str(args.iso),
        "final_hashes": final_hashes,
        "base_corrected_iso": str(args.base_fixed),
        "original_iso": {"path": str(args.original), **original_hashes, "expected_sha256": EXPECTED_ORIGINAL_SHA256, "ok": original_ok},
        "font_speaker_runtime": runtime,
        "font_speaker_runtime_ok": runtime_ok,
        "stable_regions_vs_corrected_base": stable,
        "stage_reports": stages,
        "saved_evidence": evidence,
        "ok": ok,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not ok:
        raise SystemExit(2)
    print("CURRENT-IMAGE FINAL VERIFY OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
