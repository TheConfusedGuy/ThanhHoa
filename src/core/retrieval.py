# -*- coding: utf-8 -*-
"""Core retrieval: top-k by content and speaker similarity."""

import json
import os
import sys

try:
    from stage2.voice_feature_extractor import VoiceFeatureExtractor
    from stage2.content_feature_extractor import ContentFeatureExtractor
    from core.faiss_manager import FaissManager
    from core.db_manager import DatabaseManager
except ImportError:
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from stage2.voice_feature_extractor import VoiceFeatureExtractor
    from stage2.content_feature_extractor import ContentFeatureExtractor
    from core.faiss_manager import FaissManager
    from core.db_manager import DatabaseManager


class AudioRetriever:
    def __init__(self, top_k: int = 3):
        self.top_k = top_k
        self.voice_extractor = VoiceFeatureExtractor()
        self.content_extractor = ContentFeatureExtractor()
        self.faiss_mgr = FaissManager()
        self.db_mgr = DatabaseManager()

    def search(self, audio_path: str, top_k: int = None) -> dict:
        k = top_k if top_k is not None else self.top_k
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Không tìm thấy file: {audio_path}")

        query_filename = os.path.basename(audio_path)
        content_vector, voice_vector = self._extract_query_vectors(audio_path)
        content_matches = self._search_content(content_vector, k, query_filename)
        voice_matches = self._search_voice(voice_vector, k, query_filename)
        result = {"query_file": query_filename, "content_matches": content_matches, "voice_matches": voice_matches}
        self._print_results(result)
        return result

    def _extract_query_vectors(self, audio_path: str):
        content_vector = []
        voice_vector = []
        try:
            transcript = self.content_extractor.transcribe_audio(audio_path)
            content_vector = self.content_extractor.l2_normalize(
                self.content_extractor.extract_semantic_embeddings(transcript)
            )
        except Exception as e:
            print(f"[WARN] Content extraction lỗi: {e}")
        try:
            voice_vector = self.voice_extractor.l2_normalize(
                self.voice_extractor.extract_speaker_embeddings(audio_path)
            )
        except Exception as e:
            print(f"[WARN] Voice extraction lỗi: {e}")
        return content_vector, voice_vector

    def _search_content(self, query_vector: list, k: int, query_filename: str) -> list:
        if not query_vector:
            return []
        scores, faiss_ids = self.faiss_mgr.search_content(query_vector, top_k=k + 1)
        pairs = [(float(s), int(i)) for s, i in zip(scores, faiss_ids) if i >= 0]
        pairs = self._filter_self(pairs, query_filename, "content")[:k]
        faiss_id_list = [p[1] for p in pairs]
        rows = self.db_mgr.get_record_by_faiss_ids(faiss_id_list)
        row_map = {r["content_faiss_id"]: r for r in rows}
        return self._build_result_list(pairs, row_map)

    def _search_voice(self, query_vector: list, k: int, query_filename: str) -> list:
        if not query_vector:
            return []
        scores, faiss_ids = self.faiss_mgr.search_voice(query_vector, top_k=k + 1)
        pairs = [(float(s), int(i)) for s, i in zip(scores, faiss_ids) if i >= 0]
        pairs = self._filter_self(pairs, query_filename, "voice")[:k]
        faiss_id_list = [p[1] for p in pairs]
        rows = self.db_mgr.get_records_by_voice_faiss_ids(faiss_id_list)
        row_map = {r["voice_faiss_id"]: r for r in rows}
        return self._build_result_list(pairs, row_map)

    def _filter_self(self, pairs: list, query_filename: str, index_type: str) -> list:
        if not pairs:
            return pairs
        top_score, top_id = pairs[0]
        if top_score >= 0.9999:
            rows = (
                self.db_mgr.get_record_by_faiss_ids([top_id])
                if index_type == "content"
                else self.db_mgr.get_records_by_voice_faiss_ids([top_id])
            )
            if rows and rows[0].get("filename") == query_filename:
                pairs = pairs[1:]
        return pairs

    @staticmethod
    def _build_result_list(pairs: list, row_map: dict) -> list:
        results = []
        for rank, (score, fid) in enumerate(pairs, start=1):
            row = row_map.get(fid, {})
            keywords = row.get("tfidf_keywords", {})
            if isinstance(keywords, str):
                try:
                    keywords = json.loads(keywords)
                except Exception:
                    keywords = {}
            results.append(
                {
                    "rank": rank,
                    "filename": row.get("filename", f"[faiss_id={fid}]"),
                    "file_path": row.get("file_path", ""),
                    "similarity": round(score, 6),
                    "duration_s": row.get("duration_seconds", 0.0),
                    "transcript": (row.get("transcript") or "")[:300],
                    "keywords": keywords,
                    "tfidf_keywords": keywords,
                    "faiss_id": fid,
                }
            )
        return results

    @staticmethod
    def _print_results(result: dict):
        print(f'\nKET QUA TIM KIEM -> "{result["query_file"]}"')
        print("TOP NOI DUNG:")
        for m in result.get("content_matches", []):
            print(f'  {m["rank"]}. [{m["similarity"]:.4f}] {m["filename"]}')
        print("TOP GIONG NOI:")
        for m in result.get("voice_matches", []):
            print(f'  {m["rank"]}. [{m["similarity"]:.4f}] {m["filename"]}')

    def close(self):
        self.db_mgr.close()


def main():
    if len(sys.argv) < 2:
        print("Cách dùng: python src/core/retrieval.py <đường_dẫn_file_âm_thanh> [top_k]")
        sys.exit(1)
    audio_path = sys.argv[1]
    top_k = int(sys.argv[2]) if len(sys.argv) >= 3 else 3
    retriever = AudioRetriever(top_k=top_k)
    try:
        results = retriever.search(audio_path, top_k=top_k)
        out_path = os.path.splitext(audio_path)[0] + "_retrieval_results.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"[Retriever] Kết quả đã lưu -> {out_path}")
    finally:
        retriever.close()


if __name__ == "__main__":
    main()

