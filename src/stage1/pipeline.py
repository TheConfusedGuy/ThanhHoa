# -*- coding: utf-8 -*-
"""Pipeline chạy Giai đoạn 1 và xuất index CSV."""

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .audio_processing import (
    ensure_parent,
    preprocess_audio,
    write_rejected_mirror,
    write_wav_mirror,
)
from .config import Stage1Config
from .metadata import (
    collect_audio_files,
    infer_topic_speaker,
    load_metadata_map,
    match_source_by_filename,
)

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover - fallback when tqdm unavailable
    tqdm = None


def evaluate_qc(topic_id: str, speaker_id: str, duration_s: float, cfg: Stage1Config) -> Tuple[str, str]:
    issues: List[str] = []
    if topic_id.startswith("unknown"):
        issues.append("missing_topic_label")
    if speaker_id.startswith("unknown"):
        issues.append("missing_speaker_label")
    if duration_s < cfg.std.min_duration_s:
        issues.append("duration_too_short")
    if duration_s > cfg.std.max_duration_s:
        issues.append("duration_too_long")
    if issues:
        return "FAIL", ";".join(issues)
    return "PASS", ""


def _iter_with_progress(items: List[Path]) -> Iterable[Path]:
    if tqdm is None:
        return items
    return tqdm(items, desc="Stage1 processing", unit="file")


def _build_row(i: int, src_path: Path, dst_path: Path, topic_id: str, speaker_id: str, meta: dict, source_meta: dict, status: str, issues: str) -> Dict[str, object]:
    processed_path = ""
    if dst_path and str(dst_path) not in ("", "."):
        processed_path = str(dst_path.resolve())
    source_url = source_meta.get("url", "")
    return {
        "id": i,
        "file_id": src_path.stem,
        "filename": src_path.name,
        "source_path": str(src_path.resolve()),
        "processed_file_path": processed_path,
        "speaker_id": speaker_id,
        "topic_id": topic_id,
        "duration_sec": meta.get("processed_duration_s", ""),
        "sample_rate": meta.get("sample_rate", ""),
        "source": source_url or str(src_path.resolve()),
        "source_url": source_url,
        "source_channel": source_meta.get("channel", ""),
        "status": status,
        "issues": issues,
    }


def _normalize_label(text: str, fallback: str) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = value.strip("_")
    return value or fallback


def run_stage1(cfg: Stage1Config):
    files = collect_audio_files(cfg.input_dir, cfg.std.allowed_exts)
    metadata_map = load_metadata_map(cfg.metadata_path)

    ensure_parent(cfg.index_csv)
    ensure_parent(cfg.summary_json)

    rows: List[Dict[str, object]] = []
    pass_count = 0
    fail_count = 0

    for i, audio_path in enumerate(_iter_with_progress(files), start=1):
        topic_id, speaker_id = infer_topic_speaker(cfg.input_dir, audio_path, layout=cfg.label_layout)
        source_meta = match_source_by_filename(audio_path, metadata_map)
        if speaker_id.startswith("unknown"):
            speaker_id = _normalize_label(source_meta.get("channel", ""), "unknown_speaker")
        if speaker_id.startswith("unknown") and cfg.default_speaker_id:
            speaker_id = _normalize_label(cfg.default_speaker_id, "unknown_speaker")
        if topic_id.startswith("unknown"):
            topic_id = _normalize_label(source_meta.get("playlist", ""), "unknown_topic")
        try:
            y, sr, prep_meta = preprocess_audio(audio_path, cfg.std)
            status, issues = evaluate_qc(topic_id, speaker_id, prep_meta["processed_duration_s"], cfg)

            out_path = (cfg.output_dir / audio_path.relative_to(cfg.input_dir)).with_suffix(".wav")
            if not cfg.dry_run:
                if status == "PASS":
                    out_path = write_wav_mirror(cfg.input_dir, cfg.output_dir, audio_path, y, sr)
                elif cfg.move_rejected:
                    out_path = write_rejected_mirror(cfg.input_dir, cfg.rejected_dir, audio_path)

            row = _build_row(i, audio_path, out_path if status == "PASS" else Path(""), topic_id, speaker_id, prep_meta, source_meta, status, issues)
            rows.append(row)
            if status == "PASS":
                pass_count += 1
            else:
                fail_count += 1
        except Exception as exc:
            fail_count += 1
            rows.append(
                _build_row(
                    i=i,
                    src_path=audio_path,
                    dst_path=Path(""),
                    topic_id=topic_id,
                    speaker_id=speaker_id,
                    meta={},
                    source_meta=source_meta,
                    status="FAIL",
                    issues=f"processing_error:{exc}",
                )
            )

    fieldnames = [
        "id",
        "file_id",
        "filename",
        "source_path",
        "processed_file_path",
        "speaker_id",
        "topic_id",
        "duration_sec",
        "sample_rate",
        "source",
        "source_url",
        "source_channel",
        "status",
        "issues",
    ]
    with open(cfg.index_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    unknown_topic_count = sum(1 for r in rows if str(r.get("topic_id", "")).startswith("unknown"))
    unknown_speaker_count = sum(1 for r in rows if str(r.get("speaker_id", "")).startswith("unknown"))

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "input_dir": str(cfg.input_dir.resolve()),
        "output_dir": str(cfg.output_dir.resolve()),
        "index_csv": str(cfg.index_csv.resolve()),
        "summary_json": str(cfg.summary_json.resolve()),
        "total_files_discovered": len(files),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "unknown_topic_count": unknown_topic_count,
        "unknown_speaker_count": unknown_speaker_count,
        "pass_rate": round(pass_count / len(files), 4) if files else 0.0,
        "standard": {
            "allowed_exts": list(cfg.std.allowed_exts),
            "target_sample_rate": cfg.std.target_sample_rate,
            "min_duration_s": cfg.std.min_duration_s,
            "max_duration_s": cfg.std.max_duration_s,
            "mono": cfg.std.mono,
            "trim_silence_top_db": cfg.std.trim_silence_top_db,
            "peak_target_db": cfg.std.peak_target_db,
            "enable_denoise": cfg.std.enable_denoise,
            "label_layout": cfg.label_layout,
        },
    }
    with open(cfg.summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n[STAGE1] Done")
    print(f"[STAGE1] Total/PASS/FAIL: {len(files)}/{pass_count}/{fail_count}")
    print(f"[STAGE1] dataset_index: {cfg.index_csv}")
    print(f"[STAGE1] summary: {cfg.summary_json}")
