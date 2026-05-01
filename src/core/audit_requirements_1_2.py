# -*- coding: utf-8 -*-
"""Audit completion status for requirement 1 and 2."""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class AuditConfig:
    stage1_index_csv: Path
    stage2_jsonl: Path
    output_json: Path
    min_duration_s: float
    max_duration_s: float
    content_dim: int
    voice_dim: int


def _is_unknown(value: str) -> bool:
    lowered = (value or "").strip().lower()
    return (not lowered) or lowered.startswith("unknown")


def _safe_float(value: object) -> float | None:
    try:
        val = float(value)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    except Exception:
        return None


def _validate_stage1(cfg: AuditConfig) -> Dict[str, object]:
    issues: List[Dict[str, object]] = []
    required_columns = {
        "id",
        "filename",
        "speaker_id",
        "topic_id",
        "duration_sec",
        "status",
    }
    total_rows = 0

    if not cfg.stage1_index_csv.exists():
        return {
            "passed": False,
            "total_rows": 0,
            "issues": [{"type": "missing_file", "message": f"Missing {cfg.stage1_index_csv}"}],
        }

    with cfg.stage1_index_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns = set(reader.fieldnames or [])
        missing_columns = sorted(required_columns - columns)
        if missing_columns:
            return {
                "passed": False,
                "total_rows": 0,
                "issues": [
                    {
                        "type": "missing_columns",
                        "message": f"Stage1 index missing columns: {missing_columns}",
                    }
                ],
            }

        for row in reader:
            total_rows += 1
            row_id = row.get("id", str(total_rows))
            filename = (row.get("filename") or "").strip()
            speaker_id = (row.get("speaker_id") or "").strip()
            topic_id = (row.get("topic_id") or "").strip()
            status = (row.get("status") or "").strip().upper()
            duration = _safe_float(row.get("duration_sec"))

            if status != "PASS":
                issues.append({"row_id": row_id, "filename": filename, "type": "status_not_pass"})
            if _is_unknown(topic_id):
                issues.append({"row_id": row_id, "filename": filename, "type": "missing_topic"})
            if _is_unknown(speaker_id):
                issues.append({"row_id": row_id, "filename": filename, "type": "missing_speaker"})
            if duration is None:
                issues.append({"row_id": row_id, "filename": filename, "type": "invalid_duration"})
            elif duration < cfg.min_duration_s or duration > cfg.max_duration_s:
                issues.append(
                    {
                        "row_id": row_id,
                        "filename": filename,
                        "type": "duration_out_of_range",
                        "duration_sec": duration,
                    }
                )

    if total_rows == 0:
        issues.append({"type": "empty_index", "message": "No rows found in stage1 index."})

    return {"passed": total_rows > 0 and not issues, "total_rows": total_rows, "issues": issues}


def _validate_vector(vector: object, expected_dim: int) -> Tuple[bool, str]:
    if not isinstance(vector, list):
        return False, "not_a_list"
    if len(vector) != expected_dim:
        return False, f"dim_{len(vector)}_expected_{expected_dim}"
    for item in vector:
        val = _safe_float(item)
        if val is None:
            return False, "contains_non_numeric"
    return True, ""


def _validate_stage2(cfg: AuditConfig) -> Dict[str, object]:
    issues: List[Dict[str, object]] = []
    total_rows = 0
    required_acoustic_keys = {
        "mfccs_mean",
        "mfccs_std",
        "pitch_mean",
        "pitch_std",
        "energy_mean",
        "energy_std",
        "zcr_mean",
        "zcr_std",
    }

    if not cfg.stage2_jsonl.exists():
        return {
            "passed": False,
            "total_rows": 0,
            "issues": [{"type": "missing_file", "message": f"Missing {cfg.stage2_jsonl}"}],
        }

    with cfg.stage2_jsonl.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            total_rows += 1
            try:
                rec = json.loads(line)
            except Exception:
                issues.append({"line": line_no, "type": "invalid_json"})
                continue

            file_path = str(rec.get("file_path", "")).strip()
            transcript = str(rec.get("transcript", "")).strip()
            keywords = rec.get("keywords")
            content_embedding = rec.get("content_embedding")
            speaker_embedding = rec.get("speaker_embedding")
            acoustic_features = rec.get("acoustic_features")

            if not file_path:
                issues.append({"line": line_no, "type": "missing_file_path"})
            if not transcript:
                issues.append({"line": line_no, "file_path": file_path, "type": "empty_transcript"})
            if not isinstance(keywords, dict):
                issues.append({"line": line_no, "file_path": file_path, "type": "invalid_keywords"})

            ok_content, content_reason = _validate_vector(content_embedding, cfg.content_dim)
            if not ok_content:
                issues.append(
                    {
                        "line": line_no,
                        "file_path": file_path,
                        "type": "invalid_content_embedding",
                        "reason": content_reason,
                    }
                )

            ok_voice, voice_reason = _validate_vector(speaker_embedding, cfg.voice_dim)
            if not ok_voice:
                issues.append(
                    {
                        "line": line_no,
                        "file_path": file_path,
                        "type": "invalid_speaker_embedding",
                        "reason": voice_reason,
                    }
                )

            if not isinstance(acoustic_features, dict):
                issues.append({"line": line_no, "file_path": file_path, "type": "invalid_acoustic_features"})
            else:
                missing_keys = sorted(required_acoustic_keys - set(acoustic_features.keys()))
                if missing_keys:
                    issues.append(
                        {
                            "line": line_no,
                            "file_path": file_path,
                            "type": "missing_acoustic_keys",
                            "keys": missing_keys,
                        }
                    )

    if total_rows == 0:
        issues.append({"type": "empty_features", "message": "No rows found in stage2 features jsonl."})

    return {"passed": total_rows > 0 and not issues, "total_rows": total_rows, "issues": issues}


def run_audit(cfg: AuditConfig) -> Dict[str, object]:
    stage1_result = _validate_stage1(cfg)
    stage2_result = _validate_stage2(cfg)

    summary = {
        "requirements": {
            "requirement_1_dataset_and_labels": stage1_result,
            "requirement_2_content_voice_features": stage2_result,
        },
        "overall_passed": stage1_result["passed"] and stage2_result["passed"],
        "note": "Scope excludes minimum 500 files as requested.",
    }

    cfg.output_json.parent.mkdir(parents=True, exist_ok=True)
    cfg.output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def parse_args() -> AuditConfig:
    parser = argparse.ArgumentParser(description="Audit completion status for requirement 1 and 2.")
    parser.add_argument("--stage1-index-csv", default="src/artifacts/stage1/dataset_index.csv")
    parser.add_argument("--stage2-jsonl", default="src/artifacts/stage2/stage2_features.jsonl")
    parser.add_argument("--output-json", default="src/artifacts/req12_audit.json")
    parser.add_argument("--min-duration-s", type=float, default=60.0)
    parser.add_argument("--max-duration-s", type=float, default=3600.0)
    parser.add_argument("--content-dim", type=int, default=384)
    parser.add_argument("--voice-dim", type=int, default=192)
    args = parser.parse_args()

    return AuditConfig(
        stage1_index_csv=Path(args.stage1_index_csv),
        stage2_jsonl=Path(args.stage2_jsonl),
        output_json=Path(args.output_json),
        min_duration_s=args.min_duration_s,
        max_duration_s=args.max_duration_s,
        content_dim=args.content_dim,
        voice_dim=args.voice_dim,
    )


def main():
    cfg = parse_args()
    summary = run_audit(cfg)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n[AUDIT] Saved -> {cfg.output_json}")


if __name__ == "__main__":
    main()
