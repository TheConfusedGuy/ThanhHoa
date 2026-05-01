# -*- coding: utf-8 -*-
"""Rebuild Stage1 dataset index from split folders on disk."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List

import soundfile as sf


def detect_split_role(rel_parts: List[str]) -> str:
    if not rel_parts:
        return ""
    head = rel_parts[0].lower()
    if head == "index":
        return "index"
    if head == "test_seen":
        return "query_seen"
    if head == "test_unseen":
        return "query_unseen"
    return ""


def read_duration_seconds(audio_path: Path) -> float:
    try:
        info = sf.info(str(audio_path))
        if info.samplerate > 0:
            return round(float(info.frames) / float(info.samplerate), 3)
    except Exception:
        pass
    return 0.0


def build_rows_from_fs(processed_root: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for wav in sorted(processed_root.rglob("*.wav")):
        rel_parts = list(wav.relative_to(processed_root).parts)
        split_role = detect_split_role(rel_parts)
        if not split_role:
            continue
        topic_id = rel_parts[1] if len(rel_parts) >= 2 else "unknown_topic"
        speaker_id = rel_parts[2] if len(rel_parts) >= 3 else "unknown_speaker"
        rows.append(
            {
                "file_id": wav.stem,
                "file_name_original": wav.stem,
                "topic_id": topic_id,
                "speaker_id": speaker_id,
                "duration": read_duration_seconds(wav),
                "split_role": split_role,
                "filepath": str(wav.resolve()),
                "playlist_url": "",
                "video_url": "",
            }
        )
    return rows


def write_index(index_csv: Path, rows: List[Dict[str, object]]):
    fieldnames = [
        "file_id",
        "file_name_original",
        "topic_id",
        "speaker_id",
        "duration",
        "split_role",
        "filepath",
        "playlist_url",
        "video_url",
    ]
    index_csv.parent.mkdir(parents=True, exist_ok=True)
    with index_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args():
    parser = argparse.ArgumentParser(description="Rebuild dataset_index.csv from Processed_Audio_Data split folders.")
    parser.add_argument("--processed-root", default="src/Processed_Audio_Data")
    parser.add_argument("--index-csv", default="src/artifacts/stage1/dataset_index.csv")
    return parser.parse_args()


def main():
    args = parse_args()
    processed_root = Path(args.processed_root)
    index_csv = Path(args.index_csv)
    rows = build_rows_from_fs(processed_root)
    write_index(index_csv, rows)
    by_split: Dict[str, int] = {}
    for row in rows:
        split = str(row.get("split_role", ""))
        by_split[split] = by_split.get(split, 0) + 1
    print(f"[REBUILD] rows={len(rows)} split_counts={by_split}")
    print(f"[REBUILD] saved={index_csv}")


if __name__ == "__main__":
    main()
