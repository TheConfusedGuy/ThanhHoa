# -*- coding: utf-8 -*-
"""Batch trich xuat dac trung Stage 2 cho toan bo thu muc am thanh."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import List

try:
    from stage2.content_feature_extractor import ContentFeatureExtractor
    from stage2.voice_feature_extractor import VoiceFeatureExtractor
except ImportError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from stage2.content_feature_extractor import ContentFeatureExtractor
    from stage2.voice_feature_extractor import VoiceFeatureExtractor


def resolve_input_dir() -> str:
    env_value = os.getenv("AUDIO_DIR", "").strip()
    if env_value:
        return env_value
    for candidate in ("src/Processed_Audio_Data", "Processed_Audio_Data", "src/Am_Thanh_Data", "Am_Thanh_Data"):
        if Path(candidate).exists():
            return candidate
    return "src/Processed_Audio_Data"


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


def run_batch_with_options(
    input_dir: Path,
    output_jsonl: Path,
    whisper_model: str = "base",
    stt_max_duration_s: float = 0.0,
    voice_max_duration_s: float = 0.0,
):
    content_extractor = ContentFeatureExtractor(whisper_model_name=whisper_model)
    voice_extractor = VoiceFeatureExtractor()
    audio_files = collect_audio_files(input_dir)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    stt_limit = stt_max_duration_s if stt_max_duration_s > 0 else None
    voice_limit = voice_max_duration_s if voice_max_duration_s > 0 else None

    with open(output_jsonl, "w", encoding="utf-8") as f:
        for i, audio_path in enumerate(audio_files, start=1):
            print(f"[{i}/{len(audio_files)}] {audio_path.name}", flush=True)

            transcript = content_extractor.transcribe_audio(str(audio_path), max_duration_s=stt_limit)
            keywords = content_extractor.extract_keywords(transcript)
            content_vec = content_extractor.l2_normalize(
                content_extractor.extract_semantic_embeddings(transcript)
            )

            acoustic = voice_extractor.extract_acoustic_features(str(audio_path), max_duration_s=voice_limit)
            speaker_vec = voice_extractor.l2_normalize(
                voice_extractor.extract_speaker_embeddings(str(audio_path), max_duration_s=voice_limit)
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
    parser.add_argument("--input-dir", default=resolve_input_dir())
    parser.add_argument("--output-jsonl", default="src/stage2/stage2_features.jsonl")
    parser.add_argument("--whisper-model", default="base")
    parser.add_argument(
        "--stt-max-duration-s",
        type=float,
        default=0.0,
        help="Chi lay toi da N giay dau de STT. 0 = dung toan bo file.",
    )
    parser.add_argument(
        "--voice-max-duration-s",
        type=float,
        default=0.0,
        help="Chi lay toi da N giay dau de trich dac trung voice. 0 = dung toan bo file.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    run_batch_with_options(
        input_dir=Path(args.input_dir),
        output_jsonl=Path(args.output_jsonl),
        whisper_model=args.whisper_model,
        stt_max_duration_s=args.stt_max_duration_s,
        voice_max_duration_s=args.voice_max_duration_s,
    )


if __name__ == "__main__":
    main()
