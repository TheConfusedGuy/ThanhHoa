# -*- coding: utf-8 -*-
"""Evaluate retrieval quality on a labeled manifest."""

import argparse
import csv
import json
import os
import statistics
import sys
import time
from datetime import datetime

try:
    from core.retrieval import AudioRetriever
except ImportError:
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from core.retrieval import AudioRetriever


VALID_SPLITS = {"index", "query_seen", "query_unseen"}


def read_manifest(manifest_path: str) -> list:
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Không tìm thấy manifest: {manifest_path}")
    rows = []
    with open(manifest_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"file_path", "topic_id", "speaker_id", "split"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Manifest thiếu cột: {sorted(missing)}")
        for row in reader:
            split = (row.get("split") or "").strip()
            if split not in VALID_SPLITS:
                raise ValueError(f"split không hợp lệ: {split}")
            rows.append(
                {
                    "file_path": (row.get("file_path") or "").strip(),
                    "filename": os.path.basename((row.get("file_path") or "").strip()),
                    "topic_id": (row.get("topic_id") or "").strip(),
                    "speaker_id": (row.get("speaker_id") or "").strip(),
                    "split": split,
                }
            )
    return rows


def safe_mean(values: list) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def precision_at_k(matches: list, label_map: dict, expected_label: str, label_key: str, top_k: int) -> float:
    if not matches:
        return 0.0
    selected = matches[:top_k]
    hit = 0
    for item in selected:
        candidate = label_map.get(item.get("filename", ""))
        if candidate and candidate.get(label_key) == expected_label:
            hit += 1
    return hit / top_k if top_k > 0 else 0.0


def evaluate(manifest_path: str, top_k: int, output_dir: str) -> dict:
    rows = read_manifest(manifest_path)
    label_map = {row["filename"]: row for row in rows}
    query_rows = [r for r in rows if r["split"] in ("query_seen", "query_unseen")]
    os.makedirs(output_dir, exist_ok=True)

    detail_path = os.path.join(output_dir, "retrieval_eval_details.jsonl")
    summary_path = os.path.join(output_dir, "retrieval_eval_summary.json")
    retriever = AudioRetriever(top_k=top_k)
    detail_records = []

    try:
        for row in query_rows:
            q_path = row["file_path"]
            if not os.path.exists(q_path):
                continue
            t0 = time.perf_counter()
            result = retriever.search(q_path, top_k=top_k)
            latency_s = time.perf_counter() - t0
            detail_records.append(
                {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "query_file_path": q_path,
                    "query_filename": row["filename"],
                    "query_split": row["split"],
                    "expected_topic_id": row["topic_id"],
                    "expected_speaker_id": row["speaker_id"],
                    "top_k": top_k,
                    "latency_s": round(latency_s, 4),
                    "precision_at_k_content": round(
                        precision_at_k(result.get("content_matches", []), label_map, row["topic_id"], "topic_id", top_k), 4
                    ),
                    "precision_at_k_voice": round(
                        precision_at_k(result.get("voice_matches", []), label_map, row["speaker_id"], "speaker_id", top_k), 4
                    ),
                    "content_matches": result.get("content_matches", []),
                    "voice_matches": result.get("voice_matches", []),
                }
            )
    finally:
        retriever.close()

    with open(detail_path, "w", encoding="utf-8") as f:
        for rec in detail_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    latencies = [r["latency_s"] for r in detail_records]
    p_content_all = [r["precision_at_k_content"] for r in detail_records]
    p_voice_all = [r["precision_at_k_voice"] for r in detail_records]
    summary = {
        "manifest_path": os.path.abspath(manifest_path),
        "top_k": top_k,
        "num_queries_evaluated": len(detail_records),
        "precision_at_k_content_mean": round(safe_mean(p_content_all), 4),
        "precision_at_k_voice_mean": round(safe_mean(p_voice_all), 4),
        "latency_mean_s": round(safe_mean(latencies), 4),
        "latency_median_s": round(float(statistics.median(latencies)) if latencies else 0.0, 4),
        "detail_log_path": os.path.abspath(detail_path),
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[EVAL] Summary: {summary_path}")
    return summary


def parse_args():
    parser = argparse.ArgumentParser(description="Đánh giá retrieval trên tập pilot có nhãn.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--output-dir", default="src/artifacts/eval_outputs")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    evaluate(args.manifest, args.top_k, args.output_dir)

