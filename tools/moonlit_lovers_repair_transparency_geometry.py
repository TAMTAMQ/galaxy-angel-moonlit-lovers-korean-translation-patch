#!/usr/bin/env python3
"""Repair Moonlit Lovers translated PNG alpha without rerendering.

Existing ``translated_png`` content is never rerendered and its RGB is never
replaced by a backup, quality fix, strict rework, or reference image.  This tool
may only copy the matching Japanese source PNG's alpha channel onto the *current*
translated PNG RGB.

Historical backups are audit evidence only.  In particular,
``build/image_transparency_backup/GADAT032`` and ``translated_png_백업.zip`` are
not RGB authorities unless a separate manual verification explicitly proves a
specific file is the user's Korean manual version.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "work" / "galaxy_angel_moonlit_lovers"
BASE = PROJECT / "assets/image_extraction/GADAT032/japanese_images"
SOURCE = BASE / "png"
TRANSLATED = BASE / "translated_png"
PRE_RERENDER_BACKUP = PROJECT / "build/image_transparency_backup/GADAT032"
MANUAL_AUTHORITY = PROJECT / "assets/image_extraction/manual_translated_png_authority.json"
RENDER_REPORT = BASE / "render_report.json"
OUT_REPORT = PROJECT / "build/image_compare/manual_alpha_recovery.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgba(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.array(image.convert("RGBA"), dtype=np.uint8)


def alpha_stats(arr: np.ndarray) -> dict:
    alpha = arr[:, :, 3]
    unique = np.unique(alpha)
    return {
        "width": int(arr.shape[1]),
        "height": int(arr.shape[0]),
        "alpha_min": int(alpha.min()),
        "alpha_max": int(alpha.max()),
        "zero_alpha": int((alpha == 0).sum()),
        "partial_alpha": int(((alpha > 0) & (alpha < 255)).sum()),
        "opaque_alpha": int((alpha == 255).sum()),
        "unique_alpha_values": int(len(unique)),
    }


def black_background_metrics(source: np.ndarray, translated: np.ndarray) -> dict:
    if source.shape != translated.shape:
        return {
            "size_mismatch": True,
            "source_zero_alpha": 0,
            "opaque_on_source_zero": 0,
            "dark_opaque_on_source_zero": 0,
            "loss_ratio": 1.0,
            "hard_failure": True,
        }
    source_zero = source[:, :, 3] == 0
    source_zero_count = int(source_zero.sum())
    added = source_zero & (translated[:, :, 3] > 16)
    dark = added & (translated[:, :, :3].max(axis=2) < 80)
    loss_ratio = float(added.sum() / source_zero_count) if source_zero_count else 0.0
    alpha_min = int(translated[:, :, 3].min())
    hard_failure = bool(
        source_zero_count >= 32 and loss_ratio >= 0.98 and alpha_min > 16
    )
    return {
        "size_mismatch": False,
        "source_zero_alpha": source_zero_count,
        "opaque_on_source_zero": int(added.sum()),
        "dark_opaque_on_source_zero": int(dark.sum()),
        "loss_ratio": loss_ratio,
        "hard_failure": hard_failure,
    }


def load_manual_authority() -> set[str]:
    payload = json.loads(MANUAL_AUTHORITY.read_text(encoding="utf-8"))
    names = payload.get("containers", {}).get("GADAT032", {}).get("images", [])
    return {str(name) for name in names}


def compose_manual_rgb_source_alpha(manual: np.ndarray, source: np.ndarray) -> np.ndarray:
    if manual.shape != source.shape:
        raise ValueError(f"canvas mismatch: manual={manual.shape} source={source.shape}")
    result = manual.copy()
    result[:, :, 3] = source[:, :, 3]
    return result


def update_render_report(changed_names: set[str]) -> None:
    if not changed_names or not RENDER_REPORT.is_file():
        return
    payload = json.loads(RENDER_REPORT.read_text(encoding="utf-8"))
    seen: set[str] = set()
    for item in payload.get("images", []):
        name = str(item.get("output_png") or "")
        if name not in changed_names:
            continue
        path = TRANSLATED / name
        item["sha256"] = sha256(path)
        with Image.open(path) as image:
            item["size"] = list(image.size)
        seen.add(name)
    missing = changed_names - seen
    if missing:
        raise RuntimeError(f"render_report is missing recovered PNGs: {sorted(missing)}")
    RENDER_REPORT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write recovered PNGs")
    args = parser.parse_args()

    protected = load_manual_authority()
    source_paths = sorted(SOURCE.glob("*.png"), key=lambda p: p.name.lower())
    translated_paths = {p.name: p for p in TRANSLATED.glob("*.png")}

    missing_translated = [p.name for p in source_paths if p.name not in translated_paths]
    unknown_protected = sorted(protected - {p.name for p in source_paths})
    if missing_translated:
        raise SystemExit(f"missing translated PNGs: {missing_translated}")
    if unknown_protected:
        raise SystemExit(f"manual authority lists missing source PNGs: {unknown_protected}")

    current_black_failures: set[str] = set()
    for source_path in source_paths:
        current_path = translated_paths[source_path.name]
        if black_background_metrics(rgba(source_path), rgba(current_path))["hard_failure"]:
            current_black_failures.add(source_path.name)

    candidates = protected | current_black_failures
    rows: list[dict] = []
    changed_names: set[str] = set()
    manual_backup_black_failures = 0

    for source_path in source_paths:
        name = source_path.name
        current_path = translated_paths[name]
        source_arr = rgba(source_path)
        current_arr = rgba(current_path)
        row = {
            "png": name,
            "protected_manual": name in protected,
            "candidate": name in candidates,
            "current_before_alpha": alpha_stats(current_arr),
            "current_before_black_background": black_background_metrics(source_arr, current_arr),
            "status": "scanned_ok",
        }
        if name not in candidates:
            rows.append(row)
            continue

        backup_path = PRE_RERENDER_BACKUP / name
        manual_path = current_path
        method = "preserve_current_translated_rgb_plus_source_alpha"

        manual_arr = rgba(manual_path)
        if manual_arr.shape != source_arr.shape:
            raise SystemExit(
                f"manual/source canvas mismatch for {name}: "
                f"{manual_arr.shape}!={source_arr.shape}"
            )
        manual_black = black_background_metrics(source_arr, manual_arr)
        if manual_black["hard_failure"]:
            manual_backup_black_failures += 1
        result_arr = compose_manual_rgb_source_alpha(manual_arr, source_arr)
        visible = source_arr[:, :, 3] > 0
        alpha_exact = bool(np.array_equal(result_arr[:, :, 3], source_arr[:, :, 3]))
        rgb_exact_all = bool(np.array_equal(result_arr[:, :, :3], manual_arr[:, :, :3]))
        visible_rgb_exact = bool(
            np.array_equal(result_arr[visible, :3], manual_arr[visible, :3])
        )
        result_black = black_background_metrics(source_arr, result_arr)
        if not alpha_exact or not rgb_exact_all or not visible_rgb_exact or result_black["hard_failure"]:
            raise SystemExit(f"recovery verification failed before write: {name}")

        current_vs_manual_rgb_diff = int(
            np.any(current_arr[:, :, :3] != manual_arr[:, :, :3], axis=2).sum()
        )
        current_vs_result_pixels = int(
            np.any(current_arr != result_arr, axis=2).sum()
        )
        row.update(
            {
                "method": method,
                "manual_rgb_source": str(manual_path),
                "legacy_backup_present": backup_path.is_file(),
                "legacy_backup_used": False,
                "manual_before_alpha": alpha_stats(manual_arr),
                "manual_before_black_background": manual_black,
                "current_vs_manual_rgb_changed_pixels": current_vs_manual_rgb_diff,
                "current_vs_recovered_rgba_changed_pixels": current_vs_result_pixels,
                "after_alpha": alpha_stats(result_arr),
                "after_black_background": result_black,
                "alpha_exact_source": alpha_exact,
                "rgb_exact_manual_all_pixels": rgb_exact_all,
                "visible_rgb_exact_manual": visible_rgb_exact,
                "manual_content_restored": bool(current_vs_manual_rgb_diff > 0),
                "status": "would_recover",
            }
        )

        if args.apply:
            Image.fromarray(result_arr, "RGBA").save(current_path)
            written = rgba(current_path)
            if not np.array_equal(written[:, :, 3], source_arr[:, :, 3]):
                raise SystemExit(f"written alpha mismatch: {name}")
            if not np.array_equal(written[:, :, :3], manual_arr[:, :, :3]):
                raise SystemExit(f"written RGB changed from manual authority: {name}")
            if black_background_metrics(source_arr, written)["hard_failure"]:
                raise SystemExit(f"black background remains after write: {name}")
            row["status"] = "recovered"
            row["output_sha256"] = sha256(current_path)
            changed_names.add(name)
        rows.append(row)

    if args.apply:
        update_render_report(changed_names)

    post_alpha_mismatch = []
    post_black_failures = []
    post_canvas_mismatch = []
    if args.apply:
        for source_path in source_paths:
            name = source_path.name
            source_arr = rgba(source_path)
            translated_arr = rgba(TRANSLATED / name)
            if source_arr.shape != translated_arr.shape:
                post_canvas_mismatch.append(name)
                continue
            if name in candidates and not np.array_equal(
                source_arr[:, :, 3], translated_arr[:, :, 3]
            ):
                post_alpha_mismatch.append(name)
            if black_background_metrics(source_arr, translated_arr)["hard_failure"]:
                post_black_failures.append(name)

    payload = {
        "schema": "moonlit-manual-alpha-recovery/v1",
        "apply": bool(args.apply),
        "source": str(SOURCE),
        "translated": str(TRANSLATED),
        "manual_authority_file": str(MANUAL_AUTHORITY),
        "pre_rerender_backup": str(PRE_RERENDER_BACKUP),
        "authority_count": len(source_paths),
        "translated_count": len(translated_paths),
        "protected_manual_count": len(protected),
        "current_black_failure_count_before": len(current_black_failures),
        "current_black_failures_before": sorted(current_black_failures),
        "candidate_count": len(candidates),
        "manual_backup_black_failure_count": manual_backup_black_failures,
        "recovered_count": len(changed_names) if args.apply else 0,
        "post_canvas_mismatch_count": len(post_canvas_mismatch),
        "post_canvas_mismatches": post_canvas_mismatch,
        "post_candidate_alpha_mismatch_count": len(post_alpha_mismatch),
        "post_candidate_alpha_mismatches": post_alpha_mismatch,
        "post_black_failure_count": len(post_black_failures),
        "post_black_failures": post_black_failures,
        "rows": rows,
    }
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "authority": payload["authority_count"],
                "translated": payload["translated_count"],
                "protected_manual": payload["protected_manual_count"],
                "current_black_failures_before": payload["current_black_failure_count_before"],
                "manual_backup_black_failures": payload["manual_backup_black_failure_count"],
                "candidates": payload["candidate_count"],
                "recovered": payload["recovered_count"],
                "post_canvas_mismatch": payload["post_canvas_mismatch_count"],
                "post_candidate_alpha_mismatch": payload["post_candidate_alpha_mismatch_count"],
                "post_black_failures": payload["post_black_failure_count"],
                "report": str(OUT_REPORT),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.apply and (
        post_canvas_mismatch or post_alpha_mismatch or post_black_failures
    ):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
