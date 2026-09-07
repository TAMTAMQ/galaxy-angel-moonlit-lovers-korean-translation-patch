from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

from galaxy_angel_build_subtitled_pss import parse_pictures
from galaxy_angel_pssplex_mux import frame_rate_from_es, mux


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(16 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def get_ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found

    known = Path.home() / "AppData/Local/ArNosurgeKoreanPatch/ffmpeg/ffmpeg.exe"
    if known.is_file():
        return str(known)

    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("ffmpeg is unavailable") from exc


def encode_m2v(
    ffmpeg: str,
    source: Path,
    subtitle: Path,
    output: Path,
    movie_root: Path,
    frame_rate: Fraction,
    bitrate_kbps: int,
    vbv_bytes: int,
) -> list[str]:
    src_arg = source.resolve().relative_to(movie_root.resolve()).as_posix()
    sub_arg = subtitle.resolve().relative_to(movie_root.resolve()).as_posix()
    out_arg = output.resolve().relative_to(movie_root.resolve()).as_posix()
    rate_arg = (
        str(frame_rate.numerator)
        if frame_rate.denominator == 1
        else f"{frame_rate.numerator}/{frame_rate.denominator}"
    )
    gop = max(12, round(float(frame_rate) / 2))
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-i",
        src_arg,
        "-map",
        "0:v:0",
        "-vf",
        f"ass={sub_arg}",
        "-an",
        "-c:v",
        "mpeg2video",
        "-pix_fmt",
        "yuv420p",
        "-r",
        rate_arg,
        "-aspect",
        "4:3",
        "-g",
        str(gop),
        "-bf",
        "2",
        "-b:v",
        f"{bitrate_kbps}k",
        "-minrate",
        f"{bitrate_kbps}k",
        "-maxrate",
        "6000k",
        "-bufsize",
        str(vbv_bytes),
        "-qmin",
        "2",
        "-qmax",
        "31",
        "-trellis",
        "1",
        "-f",
        "mpeg2video",
        out_arg,
    ]
    subprocess.run(cmd, cwd=movie_root, check=True)
    return cmd


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build all Moonlit Lovers subtitle-burned movies as PS2 PSS Plex-compatible streams."
    )
    ap.add_argument("--movie-root", type=Path, default=Path("movie"))
    ap.add_argument("--output-dir", type=Path, default=Path("movie/subtitled/final"))
    ap.add_argument("--report", type=Path, default=Path("build/moonlit_lovers_subtitled_pss_report.json"))
    ap.add_argument("--bitrate-kbps", type=int, default=5950)
    ap.add_argument("--vbv-bytes", type=int, default=1835008)
    ap.add_argument("--names", nargs="*")
    ap.add_argument("--skip-encode", action="store_true")
    args = ap.parse_args()

    root = args.movie_root
    originals = root / "original"
    extracted = root / "output"
    subtitles = root / "subtitles"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    all_names = sorted(p.stem for p in originals.glob("GADAT*.PSS"))
    if args.names:
        names = args.names
    else:
        names = [
            name for name in all_names
            if any(
                line.startswith("Dialogue:")
                for line in (subtitles / f"{name}.ko.ass").read_text(encoding="utf-8").splitlines()
            )
        ]
    skipped_empty = sorted(set(all_names) - set(names)) if not args.names else []
    ffmpeg = get_ffmpeg()
    results: list[dict[str, object]] = []

    for index, name in enumerate(names, 1):
        original_pss = originals / f"{name}.PSS"
        source_m2v = extracted / f"{name}.m2v"
        wav = extracted / f"{name}_pcm.wav"
        subtitle = subtitles / f"{name}.ko.ass"
        encoded_m2v = args.output_dir / f"{name}.m2v"
        pss = args.output_dir / f"{name}.PSS"
        pss_report = args.output_dir / f"{name}.pss.json"

        missing = [str(p) for p in (original_pss, source_m2v, wav, subtitle) if not p.is_file()]
        if missing:
            raise FileNotFoundError(f"{name}: missing inputs: {missing}")

        source_es = source_m2v.read_bytes()
        frame_rate = frame_rate_from_es(source_es)
        source_pictures = parse_pictures(source_es)
        print(
            f"[{index}/{len(names)}] {name}: encode {frame_rate.numerator}/{frame_rate.denominator} fps, "
            f"pictures={len(source_pictures)}",
            flush=True,
        )

        encode_cmd = None
        if not args.skip_encode:
            encode_cmd = encode_m2v(
                ffmpeg,
                source_m2v,
                subtitle,
                encoded_m2v,
                root,
                frame_rate,
                args.bitrate_kbps,
                args.vbv_bytes,
            )
        if not encoded_m2v.is_file():
            raise FileNotFoundError(f"{name}: encoded M2V missing: {encoded_m2v}")

        encoded_es = encoded_m2v.read_bytes()
        encoded_pictures = parse_pictures(encoded_es)
        if len(encoded_pictures) != len(source_pictures):
            raise ValueError(
                f"{name}: picture count mismatch: source={len(source_pictures)} encoded={len(encoded_pictures)}"
            )

        print(f"[{index}/{len(names)}] {name}: PSS mux", flush=True)
        mux_report = mux(encoded_m2v, wav, pss)
        pss_report.write_text(json.dumps(mux_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        result = {
            "name": name,
            "original_pss": str(original_pss.resolve()),
            "source_m2v": str(source_m2v.resolve()),
            "subtitle": str(subtitle.resolve()),
            "wav": str(wav.resolve()),
            "encoded_m2v": str(encoded_m2v.resolve()),
            "pss": str(pss.resolve()),
            "original_pss_bytes": original_pss.stat().st_size,
            "pss_bytes": pss.stat().st_size,
            "size_delta": pss.stat().st_size - original_pss.stat().st_size,
            "frame_rate": f"{frame_rate.numerator}/{frame_rate.denominator}",
            "source_pictures": len(source_pictures),
            "encoded_pictures": len(encoded_pictures),
            "source_m2v_sha256": sha256_file(source_m2v),
            "encoded_m2v_sha256": sha256_file(encoded_m2v),
            "pss_sha256": sha256_file(pss),
            "encode_command": encode_cmd,
            "mux_verification": mux_report["verification"],
        }
        results.append(result)
        args.report.write_text(
            json.dumps(
                {
                    "schema": "moonlit-lovers-all-subtitled-pss/v1",
                    "bitrate_kbps": args.bitrate_kbps,
                    "vbv_bytes": args.vbv_bytes,
                    "completed": len(results),
                    "requested": len(names),
                    "skipped_empty_subtitles": skipped_empty,
                    "results": results,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(
            f"[{index}/{len(names)}] {name}: OK pss={pss.stat().st_size} delta={result['size_delta']}",
            flush=True,
        )

    print(f"Completed {len(results)}/{len(names)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
