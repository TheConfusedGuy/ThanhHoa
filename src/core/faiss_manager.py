# -*- coding: utf-8 -*-
"""
faiss_manager.py
----------------
Quản lý hai FAISS index cho hệ thống tìm kiếm âm thanh.
"""

import os
import numpy as np
import faiss


_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.dirname(_BASE_DIR)
_ARTIFACT_DIR = os.path.join(_SRC_DIR, "artifacts", "faiss")
CONTENT_INDEX_PATH = os.path.join(_ARTIFACT_DIR, "faiss_content.index")
VOICE_INDEX_PATH = os.path.join(_ARTIFACT_DIR, "faiss_voice.index")

CONTENT_DIM = 384
VOICE_DIM = 192


class FaissManager:
    def __init__(self):
        self.content_index = self._load_or_create(CONTENT_INDEX_PATH, CONTENT_DIM)
        self.voice_index = self._load_or_create(VOICE_INDEX_PATH, VOICE_DIM)
        print(f"[FAISS] Content index: {self.content_index.ntotal} vectors  (dim={CONTENT_DIM})")
        print(f"[FAISS] Voice index  : {self.voice_index.ntotal} vectors  (dim={VOICE_DIM})")

    @staticmethod
    def _load_or_create(path: str, dim: int) -> faiss.IndexFlatIP:
        if os.path.exists(path):
            print(f"[FAISS] Đang load index từ: {path}")
            index = faiss.read_index(path)
            if index.d != dim:
                print(f"[FAISS][WARNING] Dim không khớp ({index.d} vs {dim}). Tạo index mới.")
                index = faiss.IndexFlatIP(dim)
        else:
            print(f"[FAISS] Tạo index mới (dim={dim}): {path}")
            index = faiss.IndexFlatIP(dim)
        return index

    def add_content_vector(self, vector: list) -> int:
        return self._add_to_index(self.content_index, vector, CONTENT_DIM, "content")

    def add_voice_vector(self, vector: list) -> int:
        return self._add_to_index(self.voice_index, vector, VOICE_DIM, "voice")

    @staticmethod
    def _add_to_index(index: faiss.IndexFlatIP, vector: list, expected_dim: int, name: str) -> int:
        if not vector:
            print(f"[FAISS][WARNING] Vector {name} rỗng, bỏ qua.")
            return -1

        vec = np.array(vector, dtype=np.float32).reshape(1, -1)
        if vec.shape[1] != expected_dim:
            print(f"[FAISS][ERROR] Vector {name} có {vec.shape[1]} chiều, cần {expected_dim}.")
            return -1

        row_id = index.ntotal
        index.add(vec)
        return row_id

    def search_content(self, query_vector: list, top_k: int = 10):
        return self._search(self.content_index, query_vector, CONTENT_DIM, top_k)

    def search_voice(self, query_vector: list, top_k: int = 10):
        return self._search(self.voice_index, query_vector, VOICE_DIM, top_k)

    @staticmethod
    def _search(index: faiss.IndexFlatIP, query_vector: list, expected_dim: int, top_k: int):
        if not query_vector or index.ntotal == 0:
            return np.array([]), np.array([])
        vec = np.array(query_vector, dtype=np.float32).reshape(1, -1)
        if vec.shape[1] != expected_dim:
            print("[FAISS][ERROR] Query vector sai chiều.")
            return np.array([]), np.array([])
        k = min(top_k, index.ntotal)
        scores, ids = index.search(vec, k)
        return scores[0], ids[0]

    def save(self):
        os.makedirs(_ARTIFACT_DIR, exist_ok=True)
        faiss.write_index(self.content_index, CONTENT_INDEX_PATH)
        faiss.write_index(self.voice_index, VOICE_INDEX_PATH)
        print(f"[FAISS] Đã lưu index (content={self.content_index.ntotal}, voice={self.voice_index.ntotal})")

    def stats(self) -> dict:
        return {
            "content_index": {
                "path": CONTENT_INDEX_PATH,
                "dim": CONTENT_DIM,
                "total_vectors": self.content_index.ntotal,
            },
            "voice_index": {
                "path": VOICE_INDEX_PATH,
                "dim": VOICE_DIM,
                "total_vectors": self.voice_index.ntotal,
            },
        }

