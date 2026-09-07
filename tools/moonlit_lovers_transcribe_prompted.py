from __future__ import annotations

import argparse
import json
from pathlib import Path

from faster_whisper import WhisperModel


def main() -> None:
    ap = argparse.ArgumentParser(description="Prompted Japanese transcription for known song/narration text.")
    ap.add_argument("audio", type=Path)
    ap.add_argument("prompt", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--model", default="large-v3")
    args = ap.parse_args()

    prompt = args.prompt.read_text(encoding="utf-8").strip()
    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    segments_iter, info = model.transcribe(
        str(args.audio),
        language="ja",
        beam_size=5,
        best_of=5,
        initial_prompt=prompt,
        condition_on_previous_text=True,
        temperature=0.0,
        vad_filter=False,
        word_timestamps=True,
        no_speech_threshold=0.6,
        compression_ratio_threshold=2.4,
        log_prob_threshold=-1.0,
    )
    segments = []
    for seg in segments_iter:
        words = []
        for w in seg.words or []:
            words.append({"start": round(float(w.start), 3), "end": round(float(w.end), 3), "word": w.word})
        segments.append({
            "start": round(float(seg.start), 3),
            "end": round(float(seg.end), 3),
            "text": seg.text.strip(),
            "avg_logprob": round(float(seg.avg_logprob), 4),
            "no_speech_prob": round(float(seg.no_speech_prob), 4),
            "words": words,
        })
    out = {"source": str(args.audio), "prompt": prompt, "duration": float(info.duration), "segments": segments}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{args.audio}: {len(segments)} segments -> {args.output}")


if __name__ == "__main__":
    main()
