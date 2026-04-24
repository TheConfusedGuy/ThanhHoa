# -*- coding: utf-8 -*-
"""
retrieval.py
------------
Module Truy vấn và Tìm kiếm (Retrieval) cho hệ thống âm thanh.

Nhận một file âm thanh mới làm đầu vào, trích xuất vector, so sánh với
FAISS và trả về:
  - Top-3 files giống nhất về NỘI DUNG (Content Similarity)
  - Top-3 files giống nhất về GIỌNG NÓI (Voice Similarity)

Độ đo: Cosine Similarity (Inner Product trên L2-normalized vectors).

Sử dụng:
    # CLI
    python retrieval.py path/to/query.mp3

    # Python API
    from retrieval import AudioRetriever
    retriever = AudioRetriever()
    results = retriever.search("path/to/query.mp3", top_k=3)
"""

import sys
import os
import json

from voice_feature_extractor import VoiceFeatureExtractor
from content_feature_extractor import ContentFeatureExtractor
from faiss_manager import FaissManager
from db_manager import DatabaseManager


# ─────────────────────────────────────────────────────────────────────────────
# AudioRetriever
# ─────────────────────────────────────────────────────────────────────────────

class AudioRetriever:
    """
    Thực hiện tìm kiếm âm thanh tương đồng dựa trên vector.

    Luồng:
      1. Trích xuất Content Vector (SentenceTransformer, 384-dim)
         và Voice Vector (ECAPA-TDNN, 192-dim) từ file truy vấn
      2. Chuẩn hóa L2 cả hai vector
      3. Tìm kiếm trong FAISS → lấy top-k faiss_row_id + cosine score
      4. Tra cứu metadata từ MySQL theo faiss_row_id
      5. Ghép score + metadata → trả về kết quả có cấu trúc

    Args:
        top_k (int): Số kết quả trả về cho mỗi loại tìm kiếm. Mặc định 3.
    """

    def __init__(self, top_k: int = 3):
        self.top_k = top_k

        print('[Retriever] Đang khởi tạo các thành phần...')
        self.voice_extractor   = VoiceFeatureExtractor()
        self.content_extractor = ContentFeatureExtractor()
        self.faiss_mgr         = FaissManager()
        self.db_mgr            = DatabaseManager()

        stats = self.faiss_mgr.stats()
        print(f'[Retriever] Sẵn sàng  '
              f'(content index={stats["content_index"]["total_vectors"]} vectors, '
              f'voice index={stats["voice_index"]["total_vectors"]} vectors)')

    # ── API chính ─────────────────────────────────────────────────────────────

    def search(self, audio_path: str, top_k: int = None) -> dict:
        """
        Tìm các file âm thanh tương đồng với file truy vấn.

        Args:
            audio_path (str): Đường dẫn đến file âm thanh truy vấn (.mp3/.wav/.flac).
            top_k (int|None): Ghi đè số kết quả. Nếu None dùng self.top_k.

        Returns:
            dict: {
                "query_file"    : str,            # tên file truy vấn
                "content_matches": [              # top-k giống NỘI DUNG
                    {
                        "rank"        : int,      # thứ hạng (1-based)
                        "filename"    : str,
                        "file_path"   : str,
                        "similarity"  : float,    # cosine similarity [0..1]
                        "duration_s"  : float,
                        "transcript"  : str,
                        "tfidf_keywords": dict,
                        "faiss_id"    : int,
                    },
                    ...
                ],
                "voice_matches" : [               # top-k giống GIỌNG NÓI
                    { ... }                       # cùng cấu trúc
                ],
            }
        """
        k = top_k if top_k is not None else self.top_k

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f'Không tìm thấy file: {audio_path}')

        query_filename = os.path.basename(audio_path)
        print(f'\n[Retriever] Truy vấn: {query_filename}')
        print('─' * 55)

        # ── Bước 1: Trích xuất vector từ file truy vấn ────────────────────────
        content_vector, voice_vector = self._extract_query_vectors(audio_path)

        # ── Bước 2: Tìm kiếm FAISS ────────────────────────────────────────────
        content_matches = self._search_content(content_vector, k, query_filename)
        voice_matches   = self._search_voice(voice_vector, k, query_filename)

        result = {
            'query_file':      query_filename,
            'content_matches': content_matches,
            'voice_matches':   voice_matches,
        }

        self._print_results(result)
        return result

    # ── Trích xuất vector truy vấn ────────────────────────────────────────────

    def _extract_query_vectors(self, audio_path: str):
        """Trích xuất và chuẩn hóa L2 cả hai vector từ file truy vấn."""

        # Content vector
        content_vector = []
        try:
            transcript     = self.content_extractor.transcribe_audio(audio_path)
            raw_content    = self.content_extractor.extract_semantic_embeddings(transcript)
            content_vector = self.content_extractor.l2_normalize(raw_content)
            print(f'  ✓ Content Vector  dim={len(content_vector)}  '
                  f'(transcript: {len(transcript)} ký tự)')
        except Exception as e:
            print(f'  ✗ Content extraction lỗi: {e}')

        # Voice vector
        voice_vector = []
        try:
            raw_voice    = self.voice_extractor.extract_speaker_embeddings(audio_path)
            voice_vector = self.voice_extractor.l2_normalize(raw_voice)
            print(f'  ✓ Voice Vector    dim={len(voice_vector)}  (ECAPA-TDNN)')
        except Exception as e:
            print(f'  ✗ Voice extraction lỗi: {e}')

        return content_vector, voice_vector

    # ── Tìm kiếm FAISS + tra cứu MySQL ───────────────────────────────────────

    def _search_content(self, query_vector: list, k: int,
                        query_filename: str) -> list:
        """Tìm top-k file giống về nội dung."""
        if not query_vector:
            print('  [WARN] Content vector rỗng, bỏ qua tìm kiếm nội dung.')
            return []

        scores, faiss_ids = self.faiss_mgr.search_content(query_vector, top_k=k + 1)
        if len(faiss_ids) == 0:
            return []

        # Lọc self-match (nếu file truy vấn đã có trong DB)
        pairs = [(float(s), int(i)) for s, i in zip(scores, faiss_ids) if i >= 0]
        pairs = self._filter_self(pairs, query_filename, index_type='content')
        pairs = pairs[:k]

        # Tra cứu MySQL
        faiss_id_list = [p[1] for p in pairs]
        score_map     = {p[1]: p[0] for p in pairs}
        rows = self.db_mgr.get_record_by_faiss_ids(faiss_id_list)
        row_map = {r['content_faiss_id']: r for r in rows}

        return self._build_result_list(pairs, score_map, row_map,
                                       faiss_id_key='content_faiss_id')

    def _search_voice(self, query_vector: list, k: int,
                      query_filename: str) -> list:
        """Tìm top-k file giống về giọng nói."""
        if not query_vector:
            print('  [WARN] Voice vector rỗng, bỏ qua tìm kiếm giọng nói.')
            return []

        scores, faiss_ids = self.faiss_mgr.search_voice(query_vector, top_k=k + 1)
        if len(faiss_ids) == 0:
            return []

        pairs = [(float(s), int(i)) for s, i in zip(scores, faiss_ids) if i >= 0]
        pairs = self._filter_self(pairs, query_filename, index_type='voice')
        pairs = pairs[:k]

        faiss_id_list = [p[1] for p in pairs]
        score_map     = {p[1]: p[0] for p in pairs}
        rows = self.db_mgr.get_records_by_voice_faiss_ids(faiss_id_list)
        row_map = {r['voice_faiss_id']: r for r in rows}

        return self._build_result_list(pairs, score_map, row_map,
                                       faiss_id_key='voice_faiss_id')

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _filter_self(self, pairs: list, query_filename: str,
                     index_type: str) -> list:
        """
        Loại bỏ self-match nếu file truy vấn đã nằm trong FAISS index.
        So sánh bằng cách tra MySQL theo faiss_id, kiểm tra tên file.
        """
        if not pairs:
            return pairs
        # Lấy score cao nhất — nếu = 1.0 rất có thể là chính nó
        top_score, top_id = pairs[0]
        if top_score >= 0.9999:
            # Xác nhận qua MySQL
            if index_type == 'content':
                rows = self.db_mgr.get_record_by_faiss_ids([top_id])
            else:
                rows = self.db_mgr.get_records_by_voice_faiss_ids([top_id])
            if rows and rows[0].get('filename') == query_filename:
                pairs = pairs[1:]   # bỏ kết quả đầu (chính nó)
        return pairs

    @staticmethod
    def _build_result_list(pairs: list, score_map: dict, row_map: dict,
                           faiss_id_key: str) -> list:
        """Ghép điểm tương đồng với metadata từ MySQL thành danh sách kết quả."""
        results = []
        for rank, (score, fid) in enumerate(pairs, start=1):
            row = row_map.get(fid, {})
            # Parse tfidf_keywords nếu là chuỗi JSON
            keywords = row.get('tfidf_keywords', {})
            if isinstance(keywords, str):
                try:
                    keywords = json.loads(keywords)
                except Exception:
                    keywords = {}

            results.append({
                'rank':          rank,
                'filename':      row.get('filename', f'[faiss_id={fid}]'),
                'file_path':     row.get('file_path', ''),
                'similarity':    round(score, 6),
                'duration_s':    row.get('duration_seconds', 0.0),
                'transcript':    (row.get('transcript') or '')[:300],  # cắt ngắn khi in
                'tfidf_keywords': keywords,
                'faiss_id':      fid,
            })
        return results

    # ── In kết quả ra console ─────────────────────────────────────────────────

    @staticmethod
    def _print_results(result: dict):
        """In kết quả tìm kiếm ra console theo định dạng dễ đọc."""
        print(f'\n{"═" * 55}')
        print(f'  KẾT QUẢ TÌM KIẾM  →  "{result["query_file"]}"')
        print(f'{"═" * 55}')

        # ── Content matches ────────────────────────────────────────────────────
        print('\n  📄 TOP FILE GIỐNG VỀ NỘI DUNG:')
        if result['content_matches']:
            for m in result['content_matches']:
                kw_str = ', '.join(list(m['tfidf_keywords'].keys())[:5])
                print(f'  {m["rank"]}. [{m["similarity"]:.4f}] {m["filename"]}')
                print(f'       Thời lượng : {m["duration_s"]:.1f}s')
                print(f'       Từ khóa    : {kw_str or "(không có)"}')
                if m['transcript']:
                    print(f'       Transcript : {m["transcript"][:120]}...')
                print()
        else:
            print('  (Không tìm thấy kết quả — index có thể chưa có dữ liệu)\n')

        # ── Voice matches ──────────────────────────────────────────────────────
        print('  🎙️  TOP FILE GIỐNG VỀ GIỌNG NÓI:')
        if result['voice_matches']:
            for m in result['voice_matches']:
                print(f'  {m["rank"]}. [{m["similarity"]:.4f}] {m["filename"]}')
                print(f'       Thời lượng : {m["duration_s"]:.1f}s')
                print()
        else:
            print('  (Không tìm thấy kết quả — index có thể chưa có dữ liệu)\n')

        print('═' * 55)

    # ── Giải phóng tài nguyên ─────────────────────────────────────────────────

    def close(self):
        """Đóng kết nối MySQL."""
        self.db_mgr.close()


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point:  python retrieval.py <audio_file>
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print('Cách dùng: python retrieval.py <đường_dẫn_file_âm_thanh> [top_k]')
        print('Ví dụ    : python retrieval.py query.mp3 3')
        sys.exit(1)

    audio_path = sys.argv[1]
    top_k      = int(sys.argv[2]) if len(sys.argv) >= 3 else 3

    retriever = AudioRetriever(top_k=top_k)
    try:
        results = retriever.search(audio_path, top_k=top_k)

        # Lưu kết quả ra file JSON bên cạnh file truy vấn
        out_path = os.path.splitext(audio_path)[0] + '_retrieval_results.json'
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f'\n[Retriever] Kết quả đã lưu → {out_path}')
    finally:
        retriever.close()


if __name__ == '__main__':
    main()
