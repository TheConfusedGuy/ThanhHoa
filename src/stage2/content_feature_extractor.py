# -*- coding: utf-8 -*-
"""
Stage 2 - Content feature extractor
-----------------------------------
Rang buoc pham vi:
- Dung Whisper de STT
- Dung YAKE + ViTokenizer de trich xuat keyword
- Dung SentenceTransformer (BERT-family) de tao semantic embedding
- Khong dung TF-IDF, khong dung Word2Vec
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import whisper
import yake
from pyvi import ViTokenizer
from sentence_transformers import SentenceTransformer


class ContentFeatureExtractor:
    """
    Trich xuat dac trung noi dung cho bai toan retrieval.
    """

    def __init__(
        self,
        whisper_model_name: str = "base",
        embedding_model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
    ):
        print(f"[Stage2][Content] Loading Whisper model: {whisper_model_name}")
        self.whisper_model = whisper.load_model(whisper_model_name)

        print(f"[Stage2][Content] Loading SentenceTransformer: {embedding_model_name}")
        self.embedding_model = SentenceTransformer(embedding_model_name)

        # YAKE score cang thap thi keyword cang quan trong.
        self.yake_extractor = yake.KeywordExtractor(
            lan="vi",
            n=2,
            dedupLim=0.7,
            top=10,
            features=None,
        )

    def transcribe_audio(self, audio_path: str, max_duration_s: float | None = None) -> str:
        """
        STT: chuyen am thanh thanh van ban.
        """
        try:
            if max_duration_s and max_duration_s > 0:
                audio = whisper.load_audio(audio_path)
                max_samples = int(max_duration_s * 16000)
                if audio.shape[0] > max_samples:
                    audio = audio[:max_samples]
                result = self.whisper_model.transcribe(audio, language="vi")
            else:
                result = self.whisper_model.transcribe(audio_path, language="vi")
            return (result.get("text") or "").strip()
        except Exception as exc:
            print(f"[Stage2][Content][ERROR] transcribe_audio: {audio_path} -> {exc}")
            return ""

    def extract_keywords(self, text: str, max_keywords: int = 10) -> Dict[str, float]:
        """
        YAKE + ViTokenizer:
        - Tach tu tieng Viet truoc khi chay YAKE
        - Chuan hoa score ve [0,1], cao hon la quan trong hon
        """
        try:
            if not text or not text.strip():
                return {}

            tokenized_text = ViTokenizer.tokenize(text)
            raw_keywords = self.yake_extractor.extract_keywords(tokenized_text)
            if not raw_keywords:
                return {}

            max_score = max(score for _, score in raw_keywords)
            if max_score <= 0:
                return {kw: 1.0 for kw, _ in raw_keywords[:max_keywords]}

            keywords = {
                kw.strip(): round(1.0 - (score / max_score), 4)
                for kw, score in raw_keywords[:max_keywords]
                if kw and kw.strip()
            }
            return dict(sorted(keywords.items(), key=lambda item: item[1], reverse=True))
        except Exception as exc:
            print(f"[Stage2][Content][ERROR] extract_keywords: {exc}")
            return {}

    def extract_semantic_embeddings(self, text: str) -> List[float]:
        """
        Semantic embedding (BERT-family sentence embedding).
        """
        try:
            if not text:
                return []
            embedding = self.embedding_model.encode([text], convert_to_numpy=True)[0]
            return embedding.tolist()
        except Exception as exc:
            print(f"[Stage2][Content][ERROR] extract_semantic_embeddings: {exc}")
            return []

    @staticmethod
    def l2_normalize(vector: List[float]) -> List[float]:
        if not vector:
            return []
        vec = np.array(vector, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vec.tolist()
        return (vec / norm).tolist()

