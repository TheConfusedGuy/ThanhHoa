# -*- coding: utf-8 -*-
"""Stage 3 - Build hybrid database (SQLite + FAISS) from Stage 2 output."""

from __future__ import annotations

import argparse
import json
import sqlite3
import csv
from pathlib import Path
from typing import Dict, Iterable, List

import faiss
import numpy as np


CONTENT_DIM = 384
VOICE_DIM = 192


def prepare_vector_for_ip_cosine(vector: List[float], expected_dim: int) -> np.ndarray | None:
    """
    Quy tắc bắt buộc cho Hybrid Architecture:
    - ép vector về float32
    - chuẩn hóa L2 bằng faiss.normalize_L2
    - dùng cho IndexFlatIP để tương đương cosine similarity
    """
    if not vector:
        return None
    arr = np.asarray(vector, dtype=np.float32).reshape(1, -1)
    if arr.shape[1] != expected_dim:
        return None
    faiss.normalize_L2(arr)
    return arr


def iter_jsonl(path: Path) -> Iterable[Dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def derive_file_id(file_path: Path) -> str:
    return file_path.stem.replace(" ", "_")


def derive_duration(record: Dict) -> float:
    # Stage2 output currently does not carry duration field.
    # Keep zero as safe default for report schema.
    return float(record.get("duration", 0.0) or 0.0)


def init_sqlite(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audio_metadata (
            file_id TEXT PRIMARY KEY,
            file_name TEXT NOT NULL,
            transcript_text TEXT,
            keywords TEXT,
            duration REAL DEFAULT 0,
            file_path TEXT NOT NULL,
            content_faiss_id INTEGER NOT NULL,
            voice_faiss_id INTEGER NOT NULL
        );
        """
    )
    conn.commit()
    return conn


def build_database(
    stage2_jsonl: Path,
    sqlite_path: Path,
    content_index_path: Path,
    voice_index_path: Path,
    manifest_csv: Path | None = None,
    index_split_role: str = "index",
):
    if not stage2_jsonl.exists():
        raise FileNotFoundError(f"Missing Stage2 output: {stage2_jsonl}")

    print("[Stage3] Initializing Hybrid Architecture (SQLite + FAISS IndexFlatIP)")
    print(f"[Stage3] Input features: {stage2_jsonl}")

    content_index = faiss.IndexFlatIP(CONTENT_DIM)
    voice_index = faiss.IndexFlatIP(VOICE_DIM)
    conn = init_sqlite(sqlite_path)
    cursor = conn.cursor()
    allowed_paths: set[str] | None = None

    total = 0
    inserted = 0
    skipped = 0

    if manifest_csv is not None:
        if not manifest_csv.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_csv}")
        allowed_paths = set()
        with manifest_csv.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            required = {"filepath", "split_role"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"Manifest missing columns: {sorted(missing)}")
            for row in reader:
                if str(row.get("split_role", "")).strip() != index_split_role:
                    continue
                fp = str(row.get("filepath", "")).strip()
                if fp:
                    allowed_paths.add(str(Path(fp).resolve()))
        print(f"[Stage3] Loaded manifest filter: {len(allowed_paths)} files with split_role={index_split_role}")

    cursor.execute("DELETE FROM audio_metadata")
    conn.commit()

    for rec in iter_jsonl(stage2_jsonl):
        total += 1
        file_path = Path(str(rec.get("file_path", "")))
        file_path_abs = str(file_path.resolve())
        if allowed_paths is not None and file_path_abs not in allowed_paths:
            continue
        file_id = derive_file_id(file_path)
        file_name = file_path.name or f"unknown_{total}"
        transcript = str(rec.get("transcript", "") or "")
        keywords = rec.get("keywords", {})

        content_vec = prepare_vector_for_ip_cosine(rec.get("content_embedding", []), CONTENT_DIM)
        voice_vec = prepare_vector_for_ip_cosine(rec.get("speaker_embedding", []), VOICE_DIM)

        if content_vec is None or voice_vec is None:
            skipped += 1
            print(f"[SKIP] {file_name} - invalid vector dimensions")
            continue

        content_faiss_id = int(content_index.ntotal)
        voice_faiss_id = int(voice_index.ntotal)
        content_index.add(content_vec)
        voice_index.add(voice_vec)

        cursor.execute(
            """
            INSERT OR REPLACE INTO audio_metadata (
                file_id, file_name, transcript_text, keywords, duration,
                file_path, content_faiss_id, voice_faiss_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                file_name,
                transcript,
                json.dumps(keywords, ensure_ascii=False),
                derive_duration(rec),
                file_path_abs,
                content_faiss_id,
                voice_faiss_id,
            ),
        )
        inserted += 1
        if inserted % 10 == 0:
            conn.commit()
            print(
                f"[PROGRESS] SQLite inserted={inserted} | "
                f"FAISS content={content_index.ntotal} voice={voice_index.ntotal}"
            )

    conn.commit()

    content_index_path.parent.mkdir(parents=True, exist_ok=True)
    voice_index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(content_index, str(content_index_path))
    faiss.write_index(voice_index, str(voice_index_path))

    summary = {
        "stage2_input": str(stage2_jsonl.resolve()),
        "manifest_csv": str(manifest_csv.resolve()) if manifest_csv else "",
        "index_split_role": index_split_role,
        "sqlite_db": str(sqlite_path.resolve()),
        "content_index": str(content_index_path.resolve()),
        "voice_index": str(voice_index_path.resolve()),
        "total_records_seen": total,
        "inserted_records": inserted,
        "skipped_records": skipped,
        "content_vectors": int(content_index.ntotal),
        "voice_vectors": int(voice_index.ntotal),
    }
    summary_path = sqlite_path.parent / "database_build_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n[DONE] Stage3 database population completed successfully")
    print(f"[DONE] SQLite records inserted: {inserted}")
    print(f"[DONE] FAISS content vectors: {content_index.ntotal}")
    print(f"[DONE] FAISS voice vectors: {voice_index.ntotal}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    conn.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Build Stage3 hybrid DB from Stage2 features.")
    parser.add_argument("--stage2-jsonl", default="src/artifacts/stage2/stage2_features.jsonl")
    parser.add_argument("--manifest-csv", default="")
    parser.add_argument("--index-split-role", default="index")
    parser.add_argument("--sqlite-db", default="src/artifacts/stage3/audio_hybrid.db")
    parser.add_argument("--content-index", default="src/artifacts/stage3/content.index")
    parser.add_argument("--voice-index", default="src/artifacts/stage3/voice.index")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_database(
        stage2_jsonl=Path(args.stage2_jsonl),
        sqlite_path=Path(args.sqlite_db),
        content_index_path=Path(args.content_index),
        voice_index_path=Path(args.voice_index),
        manifest_csv=Path(args.manifest_csv) if args.manifest_csv.strip() else None,
        index_split_role=args.index_split_role,
    )
