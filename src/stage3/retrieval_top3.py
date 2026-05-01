# -*- coding: utf-8 -*-
"""Stage 3 - Query top-3 content and speaker matches from hybrid DB."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

import faiss
import numpy as np

try:
    from stage2.content_feature_extractor import ContentFeatureExtractor
    from stage2.voice_feature_extractor import VoiceFeatureExtractor
except ImportError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from stage2.content_feature_extractor import ContentFeatureExtractor
    from stage2.voice_feature_extractor import VoiceFeatureExtractor


CONTENT_DIM = 384
VOICE_DIM = 192


def normalize_query_vector(vector: List[float], expected_dim: int) -> np.ndarray | None:
    """
    Bắt buộc chuẩn hóa L2 bằng faiss.normalize_L2 để dùng IndexFlatIP như cosine.
    """
    if not vector:
        return None
    arr = np.asarray(vector, dtype=np.float32).reshape(1, -1)
    if arr.shape[1] != expected_dim:
        return None
    faiss.normalize_L2(arr)
    return arr


def fetch_by_faiss_id(conn: sqlite3.Connection, index_col: str, faiss_id: int) -> Dict:
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT file_id, file_name, file_path, transcript_text, keywords, duration
        FROM audio_metadata
        WHERE {index_col} = ?
        LIMIT 1
        """,
        (int(faiss_id),),
    )
    row = cur.fetchone()
    if not row:
        return {}
    keywords = row[4]
    try:
        keywords = json.loads(keywords) if keywords else {}
    except Exception:
        keywords = {}
    return {
        "file_id": row[0],
        "file_name": row[1],
        "file_path": row[2],
        "transcript_text": row[3] or "",
        "keywords": keywords,
        "duration": float(row[5] or 0.0),
    }


def search_top_k(index: faiss.IndexFlatIP, query_vec: np.ndarray, top_k: int):
    k = min(top_k, index.ntotal)
    if k <= 0:
        return np.empty((1, 0), dtype=np.float32), np.empty((1, 0), dtype=np.int64)
    scores, ids = index.search(query_vec, k)
    return scores, ids


def build_matches(conn: sqlite3.Connection, ids: List[int], scores: List[float], index_col: str) -> List[Dict]:
    results: List[Dict] = []
    for rank, (fid, score) in enumerate(zip(ids, scores), start=1):
        if int(fid) < 0:
            continue
        meta = fetch_by_faiss_id(conn, index_col, fid)
        if not meta:
            continue
        results.append(
            {
                "rank": rank,
                "file_id": meta["file_id"],
                "file_name": meta["file_name"],
                "file_path": meta["file_path"],
                "similarity": round(float(score), 6),
                "cosine_distance": round(1.0 - float(score), 6),
                "keywords": meta["keywords"],
                "transcript_preview": meta["transcript_text"][:240],
            }
        )
    return sorted(results, key=lambda item: item["similarity"], reverse=True)


def run_query(
    query_audio: Path,
    sqlite_db: Path,
    content_index_path: Path,
    voice_index_path: Path,
    top_k: int,
    whisper_model: str,
    stt_max_duration_s: float,
    voice_max_duration_s: float,
    output_log: Path,
    verbose: bool = True,
    content_extractor: Optional[ContentFeatureExtractor] = None,
    voice_extractor: Optional[VoiceFeatureExtractor] = None,
):
    if not query_audio.exists():
        raise FileNotFoundError(f"Query audio not found: {query_audio}")
    if not sqlite_db.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_db}")
    if not content_index_path.exists():
        raise FileNotFoundError(f"Content index not found: {content_index_path}")
    if not voice_index_path.exists():
        raise FileNotFoundError(f"Voice index not found: {voice_index_path}")

    conn = sqlite3.connect(str(sqlite_db))
    content_index = faiss.read_index(str(content_index_path))
    voice_index = faiss.read_index(str(voice_index_path))

    if content_extractor is None:
        content_extractor = ContentFeatureExtractor(whisper_model_name=whisper_model)
    if voice_extractor is None:
        voice_extractor = VoiceFeatureExtractor()

    transcript = content_extractor.transcribe_audio(str(query_audio), max_duration_s=stt_max_duration_s or None)
    query_content = normalize_query_vector(
        content_extractor.extract_semantic_embeddings(transcript),
        CONTENT_DIM,
    )
    query_voice = normalize_query_vector(
        voice_extractor.extract_speaker_embeddings(str(query_audio), max_duration_s=voice_max_duration_s or None),
        VOICE_DIM,
    )
    if query_content is None or query_voice is None:
        raise RuntimeError("Failed to build query vectors for content/voice.")

    if verbose:
        # Bắt buộc in shape vector query cho báo cáo.
        print(f"[DEBUG] query_content shape: {query_content.shape}")
        print(f"[DEBUG] query_voice shape: {query_voice.shape}")

    d_content, i_content = search_top_k(content_index, query_content, top_k)
    d_voice, i_voice = search_top_k(voice_index, query_voice, top_k)

    if verbose:
        # Bắt buộc in trực tiếp ma trận cosine score trả về từ FAISS.
        print("[DEBUG] D_content (cosine scores matrix):")
        print(d_content)
        print("[DEBUG] D_voice (cosine scores matrix):")
        print(d_voice)

    content_scores = [float(x) for x in d_content[0].tolist()]
    content_ids = [int(x) for x in i_content[0].tolist()]
    voice_scores = [float(x) for x in d_voice[0].tolist()]
    voice_ids = [int(x) for x in i_voice[0].tolist()]

    content_matches = build_matches(conn, content_ids, content_scores, "content_faiss_id")
    voice_matches = build_matches(conn, voice_ids, voice_scores, "voice_faiss_id")

    output = {
        "query_file": str(query_audio.resolve()),
        "top_k": top_k,
        "query_transcript": transcript,
        "query_vector_shapes": {
            "content_shape": list(query_content.shape),
            "voice_shape": list(query_voice.shape),
        },
        "query_vectors_preview": {
            "content_first_8": query_content[0][:8].round(6).tolist(),
            "voice_first_8": query_voice[0][:8].round(6).tolist(),
        },
        "distance_matrix_logs": {
            "content_D_matrix": d_content.round(6).tolist(),
            "content_I_matrix": i_content.tolist(),
            "content_similarity_scores": [round(float(x), 6) for x in content_scores],
            "content_cosine_distances": [round(1.0 - float(x), 6) for x in content_scores],
            "voice_D_matrix": d_voice.round(6).tolist(),
            "voice_I_matrix": i_voice.tolist(),
            "voice_similarity_scores": [round(float(x), 6) for x in voice_scores],
            "voice_cosine_distances": [round(1.0 - float(x), 6) for x in voice_scores],
        },
        "content_top3": content_matches,
        "voice_top3": voice_matches,
    }

    output_log.parent.mkdir(parents=True, exist_ok=True)
    output_log.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    if verbose:
        print("\n=== PHAN 1: TOP 3 NOI DUNG GIONG NHAT ===")
        for row in content_matches:
            print(f'{row["rank"]}. [{row["similarity"]:.4f}] {row["file_name"]}')

        print("\n=== PHAN 2: TOP 3 GIONG NOI GIONG NHAT ===")
        for row in voice_matches:
            print(f'{row["rank"]}. [{row["similarity"]:.4f}] {row["file_name"]}')

        print(f"\n[LOG] Saved retrieval log: {output_log}")
    conn.close()
    return output


def parse_args():
    parser = argparse.ArgumentParser(description="Query Stage3 hybrid DB and return top-3 matches.")
    parser.add_argument("query_audio")
    parser.add_argument("--sqlite-db", default="src/artifacts/stage3/audio_hybrid.db")
    parser.add_argument("--content-index", default="src/artifacts/stage3/content.index")
    parser.add_argument("--voice-index", default="src/artifacts/stage3/voice.index")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--whisper-model", default="tiny")
    parser.add_argument("--stt-max-duration-s", type=float, default=90.0)
    parser.add_argument("--voice-max-duration-s", type=float, default=90.0)
    parser.add_argument("--output-log", default="src/artifacts/stage3/retrieval_query_log.json")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_query(
        query_audio=Path(args.query_audio),
        sqlite_db=Path(args.sqlite_db),
        content_index_path=Path(args.content_index),
        voice_index_path=Path(args.voice_index),
        top_k=args.top_k,
        whisper_model=args.whisper_model,
        stt_max_duration_s=args.stt_max_duration_s,
        voice_max_duration_s=args.voice_max_duration_s,
        output_log=Path(args.output_log),
        verbose=True,
    )
