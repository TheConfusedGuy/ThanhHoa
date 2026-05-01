# -*- coding: utf-8 -*-
"""Re-extract Stage2 content fields for specific WAV paths (merge into JSONL).

Use when batch STT used a short max_duration window and produced empty transcripts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


CONTENT_EMBEDDING_DIM = 384


def main():
    parser = argparse.ArgumentParser(description="Repair Stage2 JSONL rows by file path.")
    parser.add_argument("--jsonl", default="src/artifacts/stage2/stage2_features.jsonl")
    parser.add_argument("--whisper-model", default="tiny")
    parser.add_argument(
        "--fallback-whisper-model",
        default="",
        help="Nếu transcript/embedding vẫn rỗng với model chính, thử model nặng hơn (vd: base).",
    )
    parser.add_argument(
        "--audio",
        action="append",
        required=True,
        help="Absolute or relative path to a WAV to repair (repeatable).",
    )
    args = parser.parse_args()

    jsonl_path = Path(args.jsonl)
    if not jsonl_path.exists():
        raise FileNotFoundError(jsonl_path)

    roots = [Path(p).resolve() for p in args.audio]
    fix_set = {str(p) for p in roots}

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from stage2.content_feature_extractor import ContentFeatureExtractor

    extractor = ContentFeatureExtractor(whisper_model_name=args.whisper_model)

    out_lines: list[str] = []
    repaired = 0
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            ap = str(Path(str(rec.get("file_path", ""))).resolve())
            if ap not in fix_set:
                out_lines.append(json.dumps(rec, ensure_ascii=False))
                continue

            transcript = extractor.transcribe_audio(ap, max_duration_s=None)
            keywords = extractor.extract_keywords(transcript)
            content_vec = extractor.l2_normalize(extractor.extract_semantic_embeddings(transcript))

            fb_name = (args.fallback_whisper_model or "").strip()
            if len(content_vec) != CONTENT_EMBEDDING_DIM and fb_name:
                fb = ContentFeatureExtractor(whisper_model_name=fb_name)
                transcript = fb.transcribe_audio(ap, max_duration_s=None)
                keywords = fb.extract_keywords(transcript)
                content_vec = fb.l2_normalize(fb.extract_semantic_embeddings(transcript))
                print(f"[repair][fallback {fb_name}] {Path(ap).name}: transcript_len={len(transcript)} emb_dim={len(content_vec)}")
            rec["transcript"] = transcript
            rec["keywords"] = keywords
            rec["content_embedding"] = content_vec
            out_lines.append(json.dumps(rec, ensure_ascii=False))
            repaired += 1
            print(f"[repair] {Path(ap).name}: transcript_len={len(transcript)} emb_dim={len(content_vec)}")

    jsonl_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"[repair] Updated {repaired} row(s) in {jsonl_path}")


if __name__ == "__main__":
    main()
