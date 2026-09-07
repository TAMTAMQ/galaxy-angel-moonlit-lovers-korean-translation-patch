from __future__ import annotations

import argparse
import json
from pathlib import Path

from faster_whisper import WhisperModel

GENERIC_PROMPT = (
    "タクト、ミルフィーユ、ミルフィー、ランファ、ミント、フォルテ、ヴァニラ、ちとせ、"
    "ムーンエンジェル隊、ラッキースター、クロノブレイクキャノン、シールド、エルシオール"
)


def main() -> None:
    ap = argparse.ArgumentParser(description="Second-pass movie transcription without VAD for speech under effects/music.")
    ap.add_argument("--wav-dir", type=Path, default=Path("movie/output"))
    ap.add_argument("--out-dir", type=Path, default=Path("movie/subtitles/novad"))
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--only", action="append", default=[])
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    wavs = sorted(args.wav_dir.glob("GADAT*_pcm.wav"))
    if args.only:
        wanted = set(args.only)
        wavs = [p for p in wavs if p.name.removesuffix("_pcm.wav") in wanted]

    for wav in wavs:
        stem = wav.name.removesuffix("_pcm.wav")
        seg_iter, info = model.transcribe(
            str(wav),
            language="ja",
            beam_size=5,
            best_of=5,
            initial_prompt=GENERIC_PROMPT,
            condition_on_previous_text=False,
            temperature=0.0,
            vad_filter=False,
            word_timestamps=False,
            no_speech_threshold=0.6,
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
        )
        segments = []
        for seg in seg_iter:
            text = seg.text.strip()
            if not text:
                continue
            segments.append({
                "start": round(float(seg.start), 3),
                "end": round(float(seg.end), 3),
                "text": text,
                "avg_logprob": round(float(seg.avg_logprob), 4),
                "no_speech_prob": round(float(seg.no_speech_prob), 4),
            })
        out = {
            "schema": "moonlit-lovers-movie-novad-transcript/v1",
            "source": str(wav),
            "prompt": GENERIC_PROMPT,
            "duration": float(info.duration),
            "segments": segments,
        }
        out_path = args.out_dir / f"{stem}.ja.json"
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{stem}: {len(segments)} segments -> {out_path}")


if __name__ == "__main__":
    main()
