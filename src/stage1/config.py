# -*- coding: utf-8 -*-
"""Cấu hình và tham số CLI cho Giai đoạn 1."""

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


@dataclass
class DataStandard:
    # Chuẩn đầu vào/đầu ra phục vụ đặc trưng giọng nói (MFCC/embedding)
    allowed_exts: Tuple[str, ...] = (".mp3", ".wav", ".flac", ".m4a", ".mp4")
    target_sample_rate: int = 16000
    min_duration_s: float = 60.0
    max_duration_s: float = 3600.0
    mono: bool = True
    trim_silence_top_db: int = 30
    peak_target_db: float = -1.0
    # Mặc định tắt để giữ phạm vi môn học đơn giản
    enable_denoise: bool = False
    denoise_strength: float = 1.5


@dataclass
class Stage1Config:
    input_dir: Path
    output_dir: Path
    rejected_dir: Path
    index_csv: Path
    summary_json: Path
    metadata_path: Path
    std: DataStandard
    label_layout: str
    default_speaker_id: str
    move_rejected: bool
    dry_run: bool


def parse_args() -> Stage1Config:
    parser = argparse.ArgumentParser(description="Stage 1 - Audio data preparation.")
    parser.add_argument("--input-dir", default=os.getenv("AUDIO_DIR", "Am_Thanh_Data"))
    parser.add_argument("--output-dir", default=os.getenv("PROCESSED_AUDIO_DIR", "Processed_Audio_Data"))
    parser.add_argument("--rejected-dir", default=os.getenv("REJECTED_AUDIO_DIR", "Rejected_Audio_Data"))
    parser.add_argument("--index-csv", default="src/artifacts/stage1/dataset_index.csv")
    parser.add_argument("--summary-json", default="src/artifacts/stage1/dataset_prep_summary.json")
    parser.add_argument("--metadata-path", default=os.getenv("CRAWL_METADATA_FILE", "src/artifacts/stage1/metadata.json"))
    parser.add_argument(
        "--label-layout",
        choices=["speaker_topic", "topic_speaker"],
        default=os.getenv("STAGE1_LABEL_LAYOUT", "speaker_topic"),
        help="Folder label layout under input-dir.",
    )
    parser.add_argument(
        "--default-speaker-id",
        default=os.getenv("STAGE1_DEFAULT_SPEAKER_ID", ""),
        help="Fallback speaker_id when folder/metadata cannot infer speaker.",
    )
    parser.add_argument("--min-duration-s", type=float, default=60.0)
    parser.add_argument("--max-duration-s", type=float, default=3600.0)
    parser.add_argument("--target-sr", type=int, default=16000)
    parser.add_argument("--enable-denoise", action="store_true")
    parser.add_argument("--move-rejected", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    std = DataStandard(
        target_sample_rate=args.target_sr,
        min_duration_s=args.min_duration_s,
        max_duration_s=args.max_duration_s,
        enable_denoise=args.enable_denoise,
    )
    return Stage1Config(
        input_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        rejected_dir=Path(args.rejected_dir),
        index_csv=Path(args.index_csv),
        summary_json=Path(args.summary_json),
        metadata_path=Path(args.metadata_path),
        std=std,
        label_layout=args.label_layout,
        default_speaker_id=args.default_speaker_id.strip(),
        move_rejected=args.move_rejected,
        dry_run=args.dry_run,
    )
