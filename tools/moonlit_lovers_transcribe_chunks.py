from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio


def load_pcm_wav(path: Path) -> tuple[np.ndarray, int]:
    # faster-whisper expects ndarray input at 16 kHz. decode_audio performs the
    # same FFmpeg/PyAV resampling used by the normal path-based transcribe API.
    return decode_audio(str(path), sampling_rate=16000), 16000


def main() -> None:
    parser = argparse.ArgumentParser(description="Independently transcribe fixed-size WAV chunks to avoid music/effect hallucinations.")
    parser.add_argument("--wav-dir", type=Path, default=Path("movie/output"))
    parser.add_argument("--out-dir", type=Path, default=Path("movie/subtitles/chunked"))
    parser.add_argument("--model", default="large-v3")
    parser.add_argument("--chunk-seconds", type=float, default=10.0)
    parser.add_argument("--only", action="append", default=[])
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    wavs = sorted(args.wav_dir.glob("GADAT*_pcm.wav"))
    if args.only:
        wanted = set(args.only)
        wavs = [p for p in wavs if p.name.removesuffix("_pcm.wav") in wanted]

    for wav in wavs:
        stem = wav.name.removesuffix("_pcm.wav")
        audio, rate = load_pcm_wav(wav)
        chunk_samples = max(1, int(round(args.chunk_seconds * rate)))
        segments_out = []
        chunks_out = []
        for chunk_i, start_sample in enumerate(range(0, len(audio), chunk_samples)):
            chunk = audio[start_sample:start_sample + chunk_samples]
            offset = start_sample / rate
            if len(chunk) < int(0.15 * rate):
                continue
            seg_iter, info = model.transcribe(
                chunk,
                language="ja",
                beam_size=5,
                best_of=5,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 250, "speech_pad_ms": 150},
                condition_on_previous_text=False,
                temperature=0.0,
                no_speech_threshold=0.6,
                compression_ratio_threshold=2.4,
                log_prob_threshold=-1.0,
            )
            chunk_segments = []
            for seg in seg_iter:
                text = seg.text.strip()
                if not text:
                    continue
                row = {
                    "start": round(offset + float(seg.start), 3),
                    "end": round(offset + float(seg.end), 3),
                    "text": text,
                    "avg_logprob": round(float(seg.avg_logprob), 4),
                    "no_speech_prob": round(float(seg.no_speech_prob), 4),
                    "chunk": chunk_i,
                }
                chunk_segments.append(row)
                segments_out.append(row)
            chunks_out.append({"index": chunk_i, "offset": round(offset, 3), "segments": chunk_segments})
        out = {
            "schema": "moonlit-lovers-movie-chunk-transcript/v1",
            "source": str(wav),
            "model": args.model,
            "chunk_seconds": args.chunk_seconds,
            "segments": segments_out,
            "chunks": chunks_out,
        }
        out_path = args.out_dir / f"{stem}.ja.json"
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{stem}: {len(segments_out)} segments -> {out_path}")


if __name__ == "__main__":
    main()
