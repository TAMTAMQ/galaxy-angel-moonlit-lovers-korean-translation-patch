#!/usr/bin/env python3
"""Restore only missing GADAT032 translated PNGs from translated_png_백업.zip.

Existing translated_png files are never overwritten. No rendering or image
processing is performed: missing PNG bytes are copied verbatim from the ZIP.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
BASE = PROJECT / "assets/image_extraction/GADAT032/japanese_images"
TRANSLATED = BASE / "translated_png"
BACKUP_ZIP = BASE / "translated_png_백업.zip"
REPORT = PROJECT / "build/image_compare/gadat032_restore_missing_from_backup.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    existing = {p.name for p in TRANSLATED.glob("*.png")}
    restored: list[dict] = []
    skipped_existing = 0

    with zipfile.ZipFile(BACKUP_ZIP, "r") as zf:
        members = {
            Path(name).name: name
            for name in zf.namelist()
            if name.lower().endswith(".png")
        }
        missing = sorted(set(members) - existing)

        for name in sorted(members):
            target = TRANSLATED / name
            if target.exists():
                skipped_existing += 1
                continue
            data = zf.read(members[name])
            row = {
                "png": name,
                "zip_member": members[name],
                "sha256": sha256_bytes(data),
                "size": len(data),
                "status": "would_restore",
            }
            if args.apply:
                target.write_bytes(data)
                written = target.read_bytes()
                if written != data:
                    raise SystemExit(f"byte mismatch after restore: {name}")
                row["status"] = "restored"
            restored.append(row)

    payload = {
        "schema": "moonlit-gadat032-restore-missing-from-backup/v1",
        "apply": bool(args.apply),
        "policy": {
            "existing_translated_png": "never_overwrite",
            "missing_translated_png": "copy_verbatim_from_backup_zip",
            "rerender": False,
        },
        "existing_before": len(existing),
        "backup_png_count": len(members),
        "missing_count": len(missing),
        "missing": missing,
        "restored_count": len(restored) if args.apply else 0,
        "skipped_existing_count": skipped_existing,
        "items": restored,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "existing_before": len(existing),
        "backup": len(members),
        "missing": len(missing),
        "restored": len(restored) if args.apply else 0,
        "missing_files": missing,
        "report": str(REPORT),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
