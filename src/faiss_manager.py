# -*- coding: utf-8 -*-
"""
faiss_manager.py
----------------
Quản lý hai FAISS index cho hệ thống tìm kiếm âm thanh:
  - content_index : IndexFlatIP, dim=384  (Content Vector từ SentenceTransformer)
  - voice_index   : IndexFlatIP, dim=192  (Speaker Embedding từ ECAPA-TDNN)

Dùng IndexFlatIP + L2-normalized vector  ≡  Cosine Similarity Search.
"""

import os
import numpy as np
import faiss


# ── Đường dẫn lưu index trên disk ─────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_INDEX_PATH = os.path.join(_BASE_DIR, 'faiss_content.index')
VOICE_INDEX_PATH   = os.path.join(_BASE_DIR, 'faiss_voice.index')

# ── Số chiều của từng loại vector ─────────────────────────────────────────────
CONTENT_DIM = 384   # paraphrase-multilingual-MiniLM-L12-v2
VOICE_DIM   = 192   # ECAPA-TDNN (speechbrain/spkrec-ecapa-voxceleb)


class FaissManager:
    """
    Quản lý 2 FAISS index (content & voice).

    Mỗi index dùng IndexFlatIP (Inner Product).
    Sau khi chuẩn hóa L2 thì Inner Product = Cosine Similarity.

    Row index (faiss_row_id) bắt đầu từ 0 và tương ứng với
    trường content_faiss_id / voice_faiss_id trong bảng MySQL.
    """

    def __init__(self):
        self.content_index = self._load_or_create(CONTENT_INDEX_PATH, CONTENT_DIM)
        self.voice_index   = self._load_or_create(VOICE_INDEX_PATH,   VOICE_DIM)
        print(f'[FAISS] Content index: {self.content_index.ntotal} vectors  (dim={CONTENT_DIM})')
        print(f'[FAISS] Voice index  : {self.voice_index.ntotal} vectors  (dim={VOICE_DIM})')

    # ── Khởi tạo ──────────────────────────────────────────────────────────────

    @staticmethod
    def _load_or_create(path: str, dim: int) -> faiss.IndexFlatIP:
        """Load index từ disk nếu tồn tại, ngược lại tạo mới."""
        if os.path.exists(path):
            print(f'[FAISS] Đang load index từ: {path}')
            index = faiss.read_index(path)
            # Đảm bảo dim khớp
            if index.d != dim:
                print(f'[FAISS][WARNING] Dim không khớp ({index.d} vs {dim}). Tạo index mới.')
                index = faiss.IndexFlatIP(dim)
        else:
            print(f'[FAISS] Tạo index mới (dim={dim}): {path}')
            index = faiss.IndexFlatIP(dim)
        return index

    # ── Thêm vector ───────────────────────────────────────────────────────────

    def add_content_vector(self, vector: list) -> int:
        """
        Thêm Content Vector (384-dim, đã L2 normalize) vào content_index.

        Args:
            vector: List 384 float — vector ngữ nghĩa đã chuẩn hóa L2.

        Returns:
            int: faiss_row_id (0-based) của vector vừa thêm.
                 Trả về -1 nếu vector rỗng hoặc sai chiều.
        """
        return self._add_to_index(self.content_index, vector, CONTENT_DIM, 'content')

    def add_voice_vector(self, vector: list) -> int:
        """
        Thêm Voice/Speaker Embedding (192-dim, đã L2 normalize) vào voice_index.

        Args:
            vector: List 192 float — speaker embedding đã chuẩn hóa L2.

        Returns:
            int: faiss_row_id (0-based) của vector vừa thêm.
                 Trả về -1 nếu vector rỗng hoặc sai chiều.
        """
        return self._add_to_index(self.voice_index, vector, VOICE_DIM, 'voice')

    @staticmethod
    def _add_to_index(index: faiss.IndexFlatIP, vector: list,
                      expected_dim: int, name: str) -> int:
        """Nội bộ: validate, reshape, thêm vector vào index, trả về row_id."""
        if not vector:
            print(f'[FAISS][WARNING] Vector {name} rỗng, bỏ qua.')
            return -1

        vec = np.array(vector, dtype=np.float32).reshape(1, -1)

        if vec.shape[1] != expected_dim:
            print(f'[FAISS][ERROR] Vector {name} có {vec.shape[1]} chiều, '
                  f'cần {expected_dim}. Bỏ qua.')
            return -1

        row_id = index.ntotal          # ID sẽ được gán (0-based)
        index.add(vec)                 # Thêm vào index
        return row_id

    # ── Tìm kiếm ──────────────────────────────────────────────────────────────

    def search_content(self, query_vector: list, top_k: int = 10):
        """
        Tìm top-k nội dung gần nhất theo cosine similarity.

        Args:
            query_vector: Vector truy vấn (384-dim, đã L2 normalize).
            top_k: Số kết quả trả về.

        Returns:
            Tuple (scores, faiss_row_ids) — mỗi phần tử là np.ndarray.
        """
        return self._search(self.content_index, query_vector, CONTENT_DIM, top_k)

    def search_voice(self, query_vector: list, top_k: int = 10):
        """
        Tìm top-k giọng nói gần nhất theo cosine similarity.

        Args:
            query_vector: Vector truy vấn (192-dim, đã L2 normalize).
            top_k: Số kết quả trả về.

        Returns:
            Tuple (scores, faiss_row_ids) — mỗi phần tử là np.ndarray.
        """
        return self._search(self.voice_index, query_vector, VOICE_DIM, top_k)

    @staticmethod
    def _search(index: faiss.IndexFlatIP, query_vector: list,
                expected_dim: int, top_k: int):
        if not query_vector or index.ntotal == 0:
            return np.array([]), np.array([])
        vec = np.array(query_vector, dtype=np.float32).reshape(1, -1)
        if vec.shape[1] != expected_dim:
            print(f'[FAISS][ERROR] Query vector sai chiều.')
            return np.array([]), np.array([])
        k = min(top_k, index.ntotal)
        scores, ids = index.search(vec, k)
        return scores[0], ids[0]

    # ── Lưu index ra disk ─────────────────────────────────────────────────────

    def save(self):
        """Ghi cả 2 index ra disk. Gọi sau mỗi lần thêm vector."""
        faiss.write_index(self.content_index, CONTENT_INDEX_PATH)
        faiss.write_index(self.voice_index,   VOICE_INDEX_PATH)
        print(f'[FAISS] Đã lưu index  '
              f'(content={self.content_index.ntotal}, '
              f'voice={self.voice_index.ntotal})')

    # ── Thống kê ──────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Trả về thông tin tóm tắt về 2 index."""
        return {
            'content_index': {
                'path': CONTENT_INDEX_PATH,
                'dim': CONTENT_DIM,
                'total_vectors': self.content_index.ntotal,
            },
            'voice_index': {
                'path': VOICE_INDEX_PATH,
                'dim': VOICE_DIM,
                'total_vectors': self.voice_index.ntotal,
            },
        }
