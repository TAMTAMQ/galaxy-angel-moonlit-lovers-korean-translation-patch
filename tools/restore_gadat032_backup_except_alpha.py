#!/usr/bin/env python3
"""Restore GADAT032 translated PNGs from the user backup, except alpha-repaired files.

Policy requested by the user on 2026-09-03:
- Files recorded as recovered by manual_alpha_recovery.json keep their current bytes.
- Every other translated_png that exists in translated_png_백업.zip is restored byte-for-byte.
- Files absent from the backup are left untouched and reported.
- No renderer, quality fix, strict rework, or reference override is used.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "assets/image_extraction/GADAT032/japanese_images"
TRANSLATED = BASE / "translated_png"
BACKUP_ZIP = BASE / "translated_png_백업.zip"
ALPHA_REPORT = ROOT / "build/image_compare/manual_alpha_recovery.json"
RENDER_REPORT = BASE / "render_report.json"
OUT_REPORT = ROOT / "build/image_compare/gadat032_backup_restore_except_alpha.json"
ROLLBACK_ZIP = ROOT / "build/image_compare/gadat032_before_backup_restore.zip"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_alpha_repaired() -> set[str]:
    payload = json.loads(ALPHA_REPORT.read_text(encoding="utf-8"))
    return {
        str(row["png"])
        for row in payload.get("rows", [])
        if str(row.get("status")) == "recovered"
    }


def load_backup_entries(zf: zipfile.ZipFile) -> dict[str, str]:
    entries: dict[str, str] = {}
    for member in zf.namelist():
        if not member.lower().endswith(".png"):
            continue
        name = PurePosixPath(member).name
        if name in entries:
            raise SystemExit(f"duplicate PNG basename in backup zip: {name}")
        entries[name] = member
    return entries


def update_render_report(changed: set[str]) -> None:
    payload = json.loads(RENDER_REPORT.read_text(encoding="utf-8"))
    seen: set[str] = set()
    for row in payload.get("images", []):
        name = str(row.get("output_png") or "")
        if name not in changed:
            continue
        row["sha256"] = sha256_file(TRANSLATED / name)
        seen.add(name)
    missing = changed - seen
    if missing:
        raise SystemExit(f"render_report missing restored PNGs: {sorted(missing)}")
    RENDER_REPORT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    alpha_repaired = load_alpha_repaired()
    current = {path.name: path for path in TRANSLATED.glob("*.png")}
    alpha_hash_before = {
        name: sha256_file(current[name])
        for name in sorted(alpha_repaired)
        if name in current
    }

    with zipfile.ZipFile(BACKUP_ZIP, "r") as zf:
        backup_entries = load_backup_entries(zf)
        restore_names = sorted((set(current) & set(backup_entries)) - alpha_repaired)
        missing_from_backup = sorted(set(current) - set(backup_entries))

        ROLLBACK_ZIP.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(ROLLBACK_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as rollback:
            for name in restore_names:
                rollback.write(current[name], arcname=name)

        rows = []
        for name in restore_names:
            member = backup_entries[name]
            backup_data = zf.read(member)
            before_hash = sha256_file(current[name])
            current[name].write_bytes(backup_data)
            after_data = current[name].read_bytes()
            if after_data != backup_data:
                raise SystemExit(f"byte-for-byte restore verification failed: {name}")
            rows.append(
                {
                    "png": name,
                    "before_sha256": before_hash,
                    "backup_sha256": sha256_bytes(backup_data),
                    "after_sha256": sha256_bytes(after_data),
                    "byte_exact_backup": True,
                }
            )

    alpha_changed = []
    for name, digest in alpha_hash_before.items():
        if sha256_file(current[name]) != digest:
            alpha_changed.append(name)
    if alpha_changed:
        raise SystemExit(f"alpha-repaired files changed unexpectedly: {alpha_changed}")

    update_render_report(set(restore_names))

    payload = {
        "schema": "moonlit-gadat032-backup-restore-except-alpha/v1",
        "policy": {
            "backup_is_authority_except_alpha_repaired": True,
            "rerender": False,
            "quality_fix": False,
            "strict_rework": False,
            "reference_override": False,
        },
        "current_translated_count": len(current),
        "backup_png_count": len(backup_entries),
        "alpha_repaired_preserved_count": len(alpha_hash_before),
        "alpha_repaired_preserved": sorted(alpha_hash_before),
        "restored_from_backup_count": len(restore_names),
        "restored_from_backup": restore_names,
        "missing_from_backup_count": len(missing_from_backup),
        "missing_from_backup_preserved_current": missing_from_backup,
        "alpha_repaired_changed_count": 0,
        "rollback_zip": str(ROLLBACK_ZIP),
        "rows": rows,
    }
    OUT_REPORT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "current": len(current),
                "backup": len(backup_entries),
                "alpha_preserved": len(alpha_hash_before),
                "restored": len(restore_names),
                "missing_backup": missing_from_backup,
                "alpha_changed": 0,
                "report": str(OUT_REPORT),
                "rollback": str(ROLLBACK_ZIP),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
