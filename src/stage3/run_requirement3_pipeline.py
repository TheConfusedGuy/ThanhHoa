# -*- coding: utf-8 -*-
"""Run Stage3 end-to-end with split-aware evaluation artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List

try:
    from stage3.database_builder import build_database
    from stage3.retrieval_top3 import run_query
    from stage2.content_feature_extractor import ContentFeatureExtractor
    from stage2.voice_feature_extractor import VoiceFeatureExtractor
except ImportError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from stage3.database_builder import build_database
    from stage3.retrieval_top3 import run_query
    from stage2.content_feature_extractor import ContentFeatureExtractor
    from stage2.voice_feature_extractor import VoiceFeatureExtractor


def read_manifest_rows(manifest_csv: Path) -> List[dict]:
    if not manifest_csv.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_csv}")
    with manifest_csv.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    required = {"filepath", "split_role"}
    missing = required - set(rows[0].keys() if rows else [])
    if missing:
        raise ValueError(f"Manifest missing columns: {sorted(missing)}")
    return rows


def run_pipeline(
    stage2_jsonl: Path,
    manifest_csv: Path,
    sqlite_db: Path,
    content_index: Path,
    voice_index: Path,
    query_log_json: Path,
    per_query_dir: Path,
    top_k: int,
    whisper_model: str,
    stt_max_duration_s: float,
    voice_max_duration_s: float,
):
    build_database(
        stage2_jsonl=stage2_jsonl,
        sqlite_path=sqlite_db,
        content_index_path=content_index,
        voice_index_path=voice_index,
        manifest_csv=manifest_csv,
        index_split_role="index",
    )

    rows = read_manifest_rows(manifest_csv)
    query_rows = [r for r in rows if str(r.get("split_role", "")).strip() in {"query_seen", "query_unseen"}]
    per_query_dir.mkdir(parents=True, exist_ok=True)

    content_extractor = ContentFeatureExtractor(whisper_model_name=whisper_model)
    voice_extractor = VoiceFeatureExtractor()

    merged_logs: List[Dict] = []
    for idx, row in enumerate(query_rows, start=1):
        query_path = Path(str(row.get("filepath", "")).strip())
        if not query_path.exists():
            continue
        output = run_query(
            query_audio=query_path,
            sqlite_db=sqlite_db,
            content_index_path=content_index,
            voice_index_path=voice_index,
            top_k=top_k,
            whisper_model=whisper_model,
            stt_max_duration_s=stt_max_duration_s,
            voice_max_duration_s=voice_max_duration_s,
            output_log=per_query_dir / f"query_{idx:03d}.json",
            verbose=True,
            content_extractor=content_extractor,
            voice_extractor=voice_extractor,
        )
        output["split_role"] = row.get("split_role", "")
        output["topic_id"] = row.get("topic_id", "")
        output["speaker_id"] = row.get("speaker_id", "")
        merged_logs.append(output)

    query_log_json.parent.mkdir(parents=True, exist_ok=True)
    query_log_json.write_text(json.dumps({"queries": merged_logs}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[DONE] Requirement-3 query logs saved: {query_log_json}")
    print(f"[DONE] Total queries executed: {len(merged_logs)}")


def parse_args():
    parser = argparse.ArgumentParser(description="Run split-aware Requirement-3 pipeline.")
    parser.add_argument("--stage2-jsonl", default="src/artifacts/stage2/stage2_features.jsonl")
    parser.add_argument("--manifest-csv", default="src/artifacts/stage1/dataset_index.csv")
    parser.add_argument("--sqlite-db", default="src/artifacts/stage3/audio_hybrid.db")
    parser.add_argument("--content-index", default="src/artifacts/stage3/content.index")
    parser.add_argument("--voice-index", default="src/artifacts/stage3/voice.index")
    parser.add_argument("--query-log-json", default="src/artifacts/stage3/requirement3_query_logs.json")
    parser.add_argument("--per-query-dir", default="src/artifacts/stage3/query_logs")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--whisper-model", default="tiny")
    parser.add_argument("--stt-max-duration-s", type=float, default=90.0)
    parser.add_argument("--voice-max-duration-s", type=float, default=90.0)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(
        stage2_jsonl=Path(args.stage2_jsonl),
        manifest_csv=Path(args.manifest_csv),
        sqlite_db=Path(args.sqlite_db),
        content_index=Path(args.content_index),
        voice_index=Path(args.voice_index),
        query_log_json=Path(args.query_log_json),
        per_query_dir=Path(args.per_query_dir),
        top_k=args.top_k,
        whisper_model=args.whisper_model,
        stt_max_duration_s=args.stt_max_duration_s,
        voice_max_duration_s=args.voice_max_duration_s,
    )
