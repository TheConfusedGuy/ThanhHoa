# -*- coding: utf-8 -*-
"""Batch trich xuat dac trung Stage 2 cho toan bo thu muc am thanh."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import List

from stage2.content_feature_extractor import ContentFeatureExtractor
from stage2.voice_feature_extractor import VoiceFeatureExtractor


def collect_audio_files(base_dir: Path) -> List[Path]:
    files: List[Path] = []
    for root, _, names in os.walk(base_dir):
        for name in names:
            if name.lower().endswith((".mp3", ".wav", ".flac", ".m4a", ".mp4")):
                files.append(Path(root) / name)
    return sorted(files)


def run_batch(input_dir: Path, output_jsonl: Path):
    content_extractor = ContentFeatureExtractor()
    voice_extractor = VoiceFeatureExtractor()
    audio_files = collect_audio_files(input_dir)

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    with open(output_jsonl, "w", encoding="utf-8") as f:
        for i, audio_path in enumerate(audio_files, start=1):
            print(f"[{i}/{len(audio_files)}] {audio_path.name}")

            transcript = content_extractor.transcribe_audio(str(audio_path))
            keywords = content_extractor.extract_keywords(transcript)
            content_vec = content_extractor.l2_normalize(
                content_extractor.extract_semantic_embeddings(transcript)
            )

            acoustic = voice_extractor.extract_acoustic_features(str(audio_path))
            speaker_vec = voice_extractor.l2_normalize(
                voice_extractor.extract_speaker_embeddings(str(audio_path))
            )

            record = {
                "file_path": str(audio_path.resolve()),
                "transcript": transcript,
                "keywords": keywords,
                "content_embedding": content_vec,
                "acoustic_features": acoustic,
                "speaker_embedding": speaker_vec,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"[Stage2] Done. Output: {output_jsonl}")


def parse_args():
    parser = argparse.ArgumentParser(description="Stage 2 batch feature extraction.")
    parser.add_argument("--input-dir", default=os.getenv("AUDIO_DIR", "src/Processed_Audio_Data"))
    parser.add_argument("--output-jsonl", default="src/stage2/stage2_features.jsonl")
    return parser.parse_args()


def main():
    args = parse_args()
    run_batch(input_dir=Path(args.input_dir), output_jsonl=Path(args.output_jsonl))


if __name__ == "__main__":
    main()
