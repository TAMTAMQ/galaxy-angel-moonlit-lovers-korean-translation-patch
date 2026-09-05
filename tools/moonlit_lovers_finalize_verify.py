#!/usr/bin/env python3
"""Final evidence verifier for the 2026-09-04 Moonlit Lovers integrated build."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from moonlit_lovers_apply_speaker_patch import CONTAINERS, differing_runs, read_at, root_files

EXPECTED_ORIGINAL_SHA256 = "990be804914335df22223c0070ec677ace4b5684f367dd9b04fa8ab55263a3fe"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def hash_file(path: Path, algorithms=("sha256",)) -> dict[str, str]:
    hs = {name: hashlib.new(name) for name in algorithms}
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            for h in hs.values():
                h.update(chunk)
    return {name: h.hexdigest() for name, h in hs.items()}


def compare_whole_iso(target: Path, final: Path):
    if target.stat().st_size != final.stat().st_size:
        raise RuntimeError("target/final ISO size mismatch")
    chunk_size = 8 * 1024 * 1024
    abs_pos = 0
    runs: list[tuple[int, int]] = []
    open_start: int | None = None
    target_sha = hashlib.sha256()
    final_md5 = hashlib.md5()
    final_sha1 = hashlib.sha1()
    final_sha256 = hashlib.sha256()

    with target.open("rb") as ft, final.open("rb") as ff:
        while True:
            a = ft.read(chunk_size)
            b = ff.read(chunk_size)
            if not a and not b:
                break
            if len(a) != len(b):
                raise RuntimeError("target/final read length mismatch")
            target_sha.update(a)
            final_md5.update(b)
            final_sha1.update(b)
            final_sha256.update(b)
            if a == b:
                if open_start is not None:
                    runs.append((open_start, abs_pos))
                    open_start = None
                abs_pos += len(a)
                continue
            for i, (x, y) in enumerate(zip(a, b)):
                p = abs_pos + i
                if x != y:
                    if open_start is None:
                        open_start = p
                elif open_start is not None:
                    runs.append((open_start, p))
                    open_start = None
            abs_pos += len(a)
    if open_start is not None:
        runs.append((open_start, abs_pos))

    merged: list[tuple[int, int]] = []
    for start, end in runs:
        if merged and merged[-1][1] == start:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return {
        "size": final.stat().st_size,
        "diff_runs": merged,
        "changed_bytes": sum(end - start for start, end in merged),
        "target_sha256": target_sha.hexdigest(),
        "final_hashes": {
            "md5": final_md5.hexdigest(),
            "sha1": final_sha1.hexdigest(),
            "sha256": final_sha256.hexdigest(),
        },
    }


def verify_speaker_transplant(before: Path, after: Path, target: Path, final: Path):
    bf = root_files(before)
    af = root_files(after)
    tf = root_files(target)
    ff = root_files(final)
    expected_abs_runs: list[tuple[int, int]] = []
    rows = {}

    with before.open("rb") as fbefore, after.open("rb") as fafter, target.open("rb") as ftarget, final.open("rb") as ffinal:
        for name in CONTAINERS:
            boff, bsize = bf[name]
            aoff, asize = af[name]
            toff, tsize = tf[name]
            foff, fsize = ff[name]
            if len({bsize, asize, tsize, fsize}) != 1:
                raise RuntimeError(f"{name}: container size mismatch")
            runs = differing_runs(fbefore, fafter, boff, aoff, bsize)
            mismatches = []
            changed_bytes = 0
            for start, end in runs:
                n = end - start
                old = read_at(fbefore, boff + start, n)
                new = read_at(fafter, aoff + start, n)
                current_target = read_at(ftarget, toff + start, n)
                current_final = read_at(ffinal, foff + start, n)
                if current_target != old or current_final != new:
                    mismatches.append({"offset": start, "size": n})
                expected_abs_runs.append((foff + start, foff + end))
                changed_bytes += n
            rows[name] = {
                "diff_runs": len(runs),
                "changed_bytes": changed_bytes,
                "mismatches": mismatches,
            }
    expected_abs_runs.sort()
    return rows, expected_abs_runs


def verify_image_baseline(path: Path):
    baseline = load_json(path)
    files = baseline["files"]
    missing = []
    changed = []
    for rel, expected in files.items():
        p = Path(rel)
        if not p.is_file():
            missing.append(rel)
            continue
        got = hash_file(p)["sha256"]
        if got != expected:
            changed.append({"path": rel, "expected": expected, "actual": got})
    ok = not missing and not changed and len(files) == baseline["file_count"]
    return {
        "baseline_file_count": baseline["file_count"],
        "checked_file_count": len(files),
        "baseline_aggregate_sha256": baseline["aggregate_sha256"],
        "current_aggregate_sha256": baseline["aggregate_sha256"] if ok else None,
        "missing": missing,
        "changed": changed,
        "ok": ok,
    }


def report_iso_name(value: str) -> str:
    return value.replace("\\", "/").rsplit("/", 1)[-1]


def verify_stage_reports(build: Path, target_name: str):
    checks = []

    scenario = load_json(build / "scenario_materialize_report.json")
    checks += [
        ("scenario.dialogue", scenario.get("applied_dialogue_units") == 25510),
        ("scenario.selections", scenario.get("selection_translations") == 286),
        ("scenario.selection_overflow", scenario.get("selection_overflow_count") == 0),
        ("scenario.save_labels", scenario.get("save_label_translation_patterns_applied") == 446),
        ("scenario.mission_layout", scenario.get("mission_layout_override_patterns_applied") == 12),
    ]

    tbi = load_json(build / "tbi_com_patch_report.json")
    tc = tbi["containers"]["SCENARIO"]
    tv = tbi["verification"]["SCENARIO"]
    checks += [
        ("tbi.target_iso", report_iso_name(tbi["patched_iso"]) == target_name),
        ("tbi.resources", tc["applied_resources"] == 25 and tv["verified_resources"] == 25),
        ("tbi.strings", tc["applied_strings"] == 739 and tv["verified_strings"] == 739),
        ("tbi.overflows", tc["overflows"] == []),
    ]

    expected_remaining = {
        "ADV": (1, 13),
        "GADAT000": (2, 26),
        "SLG": (281, 81223),
        "SLGRES": (81, 1994),
        "SLGSTAGE": (715, 192782),
    }
    remaining_summary = {}
    for container, (resources, strings) in expected_remaining.items():
        p = build / f"remaining_apply_{container.lower()}.json"
        r = load_json(p)
        c = r["containers"][container]
        v = r["verification"][container]
        good = (
            report_iso_name(r["patched_iso"]) == target_name
            and c["applied_resources"] == resources
            and c["applied_strings"] == strings
            and c["overflows"] == []
            and v["verified_resources"] == resources
            and v["verified_strings"] == strings
        )
        checks.append((f"remaining.{container}", good))
        remaining_summary[container] = {"resources": resources, "strings": strings, "ok": good}

    adv = load_json(build / "adv_scenario_runtime_patch_report.json")
    checks += [
        ("adv_scenario.target_iso", report_iso_name(adv["output_iso"]) == target_name),
        ("adv_scenario.runtime", adv["runtime_copies"] == 36 and adv["verification"]["verified_runtime_copies"] == 36),
        ("adv_scenario.fixed_slots", adv["relocated"] == 0 and adv["verification"]["unchanged_outside_allowed_regions"] is True),
        ("adv_scenario.resource_count", adv["verification"]["resource_count_after"] == 2395),
    ]

    expected_images = {
        "gadat030_image_patch_report.json": 134,
        "gadat031_image_patch_report.json": 0,
        "gadat032_image_patch_report.json": 398,
        "slg_image_patch_report.json": 165,
    }
    image_summary = {}
    for filename, count in expected_images.items():
        r = load_json(build / filename)
        good = report_iso_name(r["iso"]) == target_name and r["changed_count"] == count
        checks.append((f"images.{filename}", good))
        image_summary[filename] = {"changed_count": r["changed_count"], "ok": good}

    sync = load_json(build / "adv_image_fsts_sync_report.json")
    checks += [
        ("images.adv_sync.target_iso", report_iso_name(sync["iso"]) == target_name),
        ("images.adv_sync.runtime", sync["runtime_unique_offsets"] == 481 and sync["matched_fsts_resources"] == 481),
        ("images.adv_sync.strict", sync["strict_adv_resources_verified"] == 2395),
    ]

    battle = load_json(build / "battle_bank_images_report.json")
    expected_battle = {"SLGRES": 295, "SLGSTAGE": 672, "ADV": 2}
    battle_summary = {}
    for container, count in expected_battle.items():
        c = battle["containers"][container]
        good = c["targets"] == count and c["written"] == count and c["redrawn_smaller_to_fit"] == 0 and c["skipped"] == []
        checks.append((f"battle.{container}", good))
        battle_summary[container] = {"targets": count, "written": c["written"], "ok": good}

    speaker = load_json(build / "speaker_name_patch_report.json")
    checks += [
        ("speaker.names", speaker["speaker_names_patched"] == 48),
        ("speaker.known_good_readback", len(speaker["verified"]) == 3),
        ("speaker.raw_hash", speaker["patched_raw_sha256"] == "2866070ad7af74012dc281e7a32c76f6a971b362d1c883a7595a93e2ca6a4546"),
    ]

    return {
        "checks": [{"name": name, "ok": ok} for name, ok in checks],
        "remaining": remaining_summary,
        "images": image_summary,
        "battle": battle_summary,
        "ok": all(ok for _, ok in checks),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", type=Path, required=True)
    ap.add_argument("--target", type=Path, required=True)
    ap.add_argument("--before", type=Path, required=True)
    ap.add_argument("--after", type=Path, required=True)
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--original", type=Path)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()

    for p in (args.final, args.target, args.before, args.after, args.baseline):
        if not p.exists():
            raise SystemExit(f"missing required input: {p}")

    whole = compare_whole_iso(args.target, args.final)
    speaker_rows, expected_abs_runs = verify_speaker_transplant(args.before, args.after, args.target, args.final)
    actual_runs = whole["diff_runs"]
    speaker_exact = actual_runs == expected_abs_runs and whole["changed_bytes"] == 1848 and len(actual_runs) == 45
    speaker_mismatches = sum(len(row["mismatches"]) for row in speaker_rows.values())

    image_baseline = verify_image_baseline(args.baseline)
    stages = verify_stage_reports(Path("build"), args.target.name)

    original = None
    if args.original is not None and args.original.is_file():
        original_hash = hash_file(args.original)["sha256"]
        original = {
            "path": str(args.original),
            "sha256": original_hash,
            "expected_sha256": EXPECTED_ORIGINAL_SHA256,
            "ok": original_hash == EXPECTED_ORIGINAL_SHA256,
        }

    ok = speaker_exact and speaker_mismatches == 0 and image_baseline["ok"] and stages["ok"] and (original is None or original["ok"])
    report = {
        "schema": "moonlit-lovers-finalize-verify/v1",
        "final_iso": str(args.final),
        "final_size": whole["size"],
        "final_hashes": whole["final_hashes"],
        "target_iso": str(args.target),
        "target_sha256": whole["target_sha256"],
        "whole_iso_delta": {
            "diff_runs": len(actual_runs),
            "changed_bytes": whole["changed_bytes"],
            "matches_verified_speaker_patch_exactly": speaker_exact,
        },
        "speaker_transplant": {
            "containers": speaker_rows,
            "pre_post_mismatches": speaker_mismatches,
            "expected_diff_runs": len(expected_abs_runs),
            "ok": speaker_exact and speaker_mismatches == 0,
        },
        "current_image_baseline": image_baseline,
        "stage_reports": stages,
        "original_iso": original,
        "ok": ok,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not ok:
        raise SystemExit(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
