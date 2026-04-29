# -*- coding: utf-8 -*-
"""Stage 3 - Build hybrid database (SQLite + FAISS) from Stage 2 output."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List

import faiss
import numpy as np


CONTENT_DIM = 384
VOICE_DIM = 192


def l2_normalize(vector: List[float], expected_dim: int) -> np.ndarray | None:
    if not vector:
        return None
    arr = np.asarray(vector, dtype=np.float32).reshape(1, -1)
    if arr.shape[1] != expected_dim:
        return None
    norm = np.linalg.norm(arr, axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    return arr / norm


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
            file_path TEXT NOT NULL,
            transcript_text TEXT,
            keywords TEXT,
            duration REAL DEFAULT 0,
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
):
    if not stage2_jsonl.exists():
        raise FileNotFoundError(f"Missing Stage2 output: {stage2_jsonl}")

    content_index = faiss.IndexFlatIP(CONTENT_DIM)
    voice_index = faiss.IndexFlatIP(VOICE_DIM)
    conn = init_sqlite(sqlite_path)
    cursor = conn.cursor()

    total = 0
    inserted = 0
    skipped = 0

    cursor.execute("DELETE FROM audio_metadata")
    conn.commit()

    for rec in iter_jsonl(stage2_jsonl):
        total += 1
        file_path = Path(str(rec.get("file_path", "")))
        file_id = derive_file_id(file_path)
        file_name = file_path.name or f"unknown_{total}"
        transcript = str(rec.get("transcript", "") or "")
        keywords = rec.get("keywords", {})

        content_vec = l2_normalize(rec.get("content_embedding", []), CONTENT_DIM)
        voice_vec = l2_normalize(rec.get("speaker_embedding", []), VOICE_DIM)

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
                file_id, file_name, file_path, transcript_text, keywords, duration,
                content_faiss_id, voice_faiss_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                file_name,
                str(file_path),
                transcript,
                json.dumps(keywords, ensure_ascii=False),
                derive_duration(rec),
                content_faiss_id,
                voice_faiss_id,
            ),
        )
        inserted += 1
        if inserted % 20 == 0:
            conn.commit()
            print(f"[PROGRESS] inserted={inserted} / total_seen={total}")

    conn.commit()

    content_index_path.parent.mkdir(parents=True, exist_ok=True)
    voice_index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(content_index, str(content_index_path))
    faiss.write_index(voice_index, str(voice_index_path))

    summary = {
        "stage2_input": str(stage2_jsonl.resolve()),
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

    print("[DONE] Stage3 database build completed")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    conn.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Build Stage3 hybrid DB from Stage2 features.")
    parser.add_argument("--stage2-jsonl", default="src/artifacts/stage2/stage2_features.jsonl")
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
    )
