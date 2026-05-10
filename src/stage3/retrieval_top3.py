# -*- coding: utf-8 -*-
"""Stage 3 - Query top-3 content and speaker matches from hybrid DB."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional

import faiss
import numpy as np
import whisper

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


def export_scenario_audio_dir(
    export_root: Path,
    query_audio: Path,
    content_matches: List[Dict],
    voice_matches: List[Dict],
    verbose: bool = True,
) -> None:
    """Sao chép WAV truy vấn + top-k nội dung + top-k giọng vào một thư mục kịch bản."""
    export_root.mkdir(parents=True, exist_ok=True)
    input_dir = export_root / "input"
    content_dir = export_root / "top3_content"
    voice_dir = export_root / "top3_voice"
    for d in (input_dir, content_dir, voice_dir):
        d.mkdir(parents=True, exist_ok=True)

    shutil.copy2(query_audio, input_dir / query_audio.name)

    for row in content_matches:
        src = Path(row.get("file_path") or "")
        if src.is_file():
            shutil.copy2(src, content_dir / src.name)
        elif verbose:
            print(f"[WARN] Bo qua top3_content (khong tim thay file): {src}")

    for row in voice_matches:
        src = Path(row.get("file_path") or "")
        if src.is_file():
            shutil.copy2(src, voice_dir / src.name)
        elif verbose:
            print(f"[WARN] Bo qua top3_voice (khong tim thay file): {src}")

    if verbose:
        print(f"[EXPORT] Thu muc WAV kich ban: {export_root.resolve()}")


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
    export_audio_dir: Optional[Path] = None,
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

    print("\n[BƯỚC 1] Whisper: Nạp âm thanh, chia khung tín hiệu và trích xuất Log-Mel Spectrogram")
    

    audio_np = whisper.load_audio(str(query_audio))
    mel_spectrogram = whisper.log_mel_spectrogram(audio_np)
    
    print(f"   Đã nạp tín hiệu thô: {len(audio_np)} mẫu âm thanh (samples).")
    print(f"   Áp dụng Sliding Window: Đã chia thành {mel_spectrogram.shape[1]} khung tín hiệu (frames).")
    print(f"   Kích thước Ma trận Log-Mel Spectrogram thu được: {mel_spectrogram.shape[0]} dải Mel x {mel_spectrogram.shape[1]} khung.")
    
    time.sleep(2)
    print("\n[Bước 2] Whisper: Giải mã âm thanh sang Văn bản (Speech-to-Text)")
    transcript = content_extractor.transcribe_audio(str(query_audio), max_duration_s=stt_max_duration_s or None)
    print(f"   Văn bản: '{transcript}'")
    time.sleep(1)

    print("\n[Bước 3] YAKE: Trích xuất Từ khóa cốt lõi (Keyword Extraction)")
    keywords = content_extractor.extract_keywords(transcript)
    print(f"   Từ khóa (Kèm điểm số): {keywords}")
    time.sleep(1)

    print("\n[Bước 4] MiniLM: Nhúng Vector Ngữ nghĩa Không gian")
    query_content = normalize_query_vector(
        content_extractor.extract_semantic_embeddings(transcript),
        CONTENT_DIM,
    )
    print(f"   Kích thước Vector: 1 x 384")
    print(f"   Biểu diễn Vector: {np.array(query_content)[0][:5].tolist()}")
    time.sleep(1)

    print("\n" + "="*70)
    print("LUỒNG 2: TRÍCH XUẤT ĐẶC TRƯNG ÂM HỌC / GIỌNG NÓI (VOICE FLOW)")
    print("="*70)
    print("[Bước 1] Librosa: Phân tích đặc trưng Âm học vật lý (Acoustic Stats)")
    acoustic_stats = voice_extractor.extract_acoustic_features(str(query_audio), max_duration_s=voice_max_duration_s or None)
    print(f"   Độ cao (F0): {acoustic_stats['pitch_mean']:.2f} Hz")
    print(f"   Năng lượng (RMS): {acoustic_stats['energy_mean']:.4f}")
    print(f"   Cắt không (ZCR): {acoustic_stats['zcr_mean']:.4f}")
    print(f"   MFCC : {np.array(acoustic_stats['mfccs_mean'])[:3].tolist()}")
    time.sleep(1)

    print("\n[Bước 2 và 3] ECAPA-TDNN: Trích xuất Fbank và phân tích Mạng Nơ-ron Thời gian (TDNN)")
    time.sleep(1)

    print("\n[Bước 4] ECAPA-TDNN: Ép kiểu (Pooling) và Nén Vector Định danh Người nói")
    query_voice = normalize_query_vector(
        voice_extractor.extract_speaker_embeddings(str(query_audio), max_duration_s=voice_max_duration_s or None),
        VOICE_DIM,
    )
    print(f"   Kích thước Vector: 1 x 192")
    print(f"   Biểu diễn Vector: {np.array(query_voice)[0][:10].tolist()}")
    time.sleep(1)

    print("\n" + "="*70)
    print("FAISS TÌM KIẾM VECTOR (HYBRID SEARCH)")
    print("="*70)
    print("Cosine Similarity trong Không gian Đa chiều")
    time.sleep(1)

    if query_content is None or query_voice is None:
        raise RuntimeError("Failed to build query vectors for content/voice.")

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

    if export_audio_dir is not None:
        export_scenario_audio_dir(export_audio_dir, query_audio, content_matches, voice_matches, verbose=verbose)

    if verbose:
        print("\n" + "="*85)
        print("BÁO CÁO TỔNG HỢP: KẾT QUẢ SO KHỚP COSINE (COSINE SIMILARITY MATCHING)")
        print("="*85)
        print(f"[THÔNG TIN VIDEO A - ĐẦU VÀO]: {query_audio.name}")
        print(f" - Văn bản dịch được: '{transcript[:150]}...'")
        
        # Lấy tối đa 3 từ khóa
        try:
            kw_list_query = list(keywords.keys())[:3] if isinstance(keywords, dict) else keywords[:3]
        except:
            kw_list_query = []
        print(f" - Từ khóa cốt lõi: {kw_list_query}")
        
        print("\n" + "-"*85)
        print("PHẦN 1: TÌM KIẾM THEO NGỮ NGHĨA (SO SÁNH VECTOR 384-CHIỀU)")
        print("-" * 85)
        for row in content_matches:
            print(f'Top {row["rank"]}: {row["file_name"]} | Điểm Cosine: {row["similarity"]:.4f}')
            print(f'   -> Toán học: cos(θ) = (VecA · VecB) / (||VecA|| ||VecB||) = {row["similarity"]:.4f}')
            print(f'   -> Trích đoạn Video B: "{row["transcript_preview"][:120]}..."')
            try:
                kw_list_b = list(row["keywords"].keys())[:3] if isinstance(row["keywords"], dict) else row["keywords"][:3]
                print(f'   -> Từ khóa Video B: {kw_list_b}')
            except:
                pass
            print("")

        print("-" * 85)
        print("PHẦN 2: TÌM KIẾM THEO ĐỊNH DANH GIỌNG NÓI (SO SÁNH VECTOR 192-CHIỀU)")
        print("-" * 85)
        for row in voice_matches:
            print(f'Top {row["rank"]}: {row["file_name"]} | Điểm Cosine: {row["similarity"]:.4f}')
            print(f'   -> Toán học: cos(θ) = (VecA · VecB) / (||VecA|| ||VecB||) = {row["similarity"]:.4f}')
            if row["similarity"] >= 0.90:
                print('   -> Kết luận: Điểm > 0.90 -> ĐÂY CÓ THỂ LÀ CÙNG MỘT NGƯỜI NÓI.')
            else:
                print('   -> Kết luận: Điểm < 0.90 -> Có thể là người khác hoặc cùng người nhưng bị nhiễu.')
            print("")

        print(f"Toàn bộ báo cáo JSON đã được xuất ra: {output_log}")
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
    parser.add_argument(
        "--export-audio-dir",
        default=None,
        help="Neu dat, tao thu muc gom input/, top3_content/, top3_voice/ va sao chep WAV tuong ung.",
    )
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
        export_audio_dir=Path(args.export_audio_dir) if args.export_audio_dir else None,
    )
