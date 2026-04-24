# -*- coding: utf-8 -*-
import whisper
import soundfile as sf
import numpy as np
from sentence_transformers import SentenceTransformer
import yake
from pyvi import ViTokenizer
import tempfile
import os

class ContentFeatureExtractor:
    def __init__(self):
        print('Loading Whisper model...')
        self.whisper_model = whisper.load_model('base')

        # Content Vector model: đa ngôn ngữ, hỗ trợ tiếng Việt, output 384 chiều
        print('Loading SentenceTransformer model (paraphrase-multilingual-MiniLM-L12-v2)...')
        self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

        # YAKE keyword extractor — khởi tạo sẵn, tái sử dụng cho hiệu quả
        # lan='vi' để tối ưu cho tiếng Việt, n=2 cho phép bigram
        self.yake_extractor = yake.KeywordExtractor(
            lan='vi',
            n=2,            # khai thác cả unigram và bigram
            dedupLim=0.7,   # ngưỡng loại trừ từ khóa trùng lặp
            top=10,         # số từ khóa trả về
            features=None
        )

    def transcribe_audio(self, audio_path):
        try:
            import time
            # Convert MP3 to WAV if needed
            if audio_path.endswith('.mp3'):
                import librosa
                import shutil
                import tempfile
                # Create temp file name, close immediately, then copy
                temp_mp3 = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
                temp_mp3_path = temp_mp3.name
                temp_mp3.close()
                shutil.copy2(audio_path, temp_mp3_path)
                print(f"[DEBUG] Temp MP3 path: {temp_mp3_path}, exists: {os.path.exists(temp_mp3_path)}")
                time.sleep(0.1)
                if not os.path.exists(temp_mp3_path):
                    print(f"[ERROR] Temp MP3 file does not exist before librosa.load!")
                y, sr = librosa.load(temp_mp3_path, sr=16000)
                os.unlink(temp_mp3_path)  # Clean up temp MP3
                temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                temp_wav_path = temp_wav.name
                temp_wav.close()
                sf.write(temp_wav_path, y, sr)
                print(f"[DEBUG] Temp WAV path: {temp_wav_path}, exists: {os.path.exists(temp_wav_path)}")
                time.sleep(0.1)
                if not os.path.exists(temp_wav_path):
                    print(f"[ERROR] Temp WAV file does not exist before whisper.transcribe!")
                result = self.whisper_model.transcribe(temp_wav_path)
                os.unlink(temp_wav_path)  # Clean up temp WAV
            else:
                result = self.whisper_model.transcribe(audio_path)

            return result['text'].strip()
        except Exception as e:
            print(f'Error transcribing {audio_path}: {e}')
            return ''

    def extract_keywords(self, text: str, max_keywords: int = 10) -> dict:
        """
        Trích xuất từ khóa quan trọng từ văn bản tiếng Việt.

        Quy trình 2 bước:
          1. pyvi.ViTokenizer.tokenize() — tách từ tiếng Việt đúng ngữ pháp
             (ví dụ: "học sinh" giữ nguyên, không tách thành "học" + "sinh")
          2. yake.KeywordExtractor — thuật toán unsupervised, không cần corpus huấn luyện
             (YAKE score: thấp hơn = quan trọng hơn → đảo nghiịch để chuẩn hóa về [0, 1])

        Args:
            text (str): Văn bản tiếng Việt (transcript từ Whisper).
            max_keywords (int): Số từ khóa cần trả về.

        Returns:
            dict: {từ_khóa: importance_score}  — score ∈ [0, 1], cao hơn = quan trọng hơn.
        """
        try:
            if not text or not text.strip():
                return {}

            # Bước 1: Tách từ tiếng Việt
            tokenized = ViTokenizer.tokenize(text)

            # Bước 2: Trích xuất từ khóa bằng YAKE
            raw_keywords = self.yake_extractor.extract_keywords(tokenized)
            # raw_keywords: [(keyword, yake_score), ...] — score thấp = quan trọng hơn

            if not raw_keywords:
                return {}

            # Bước 3: Chuẩn hóa score về [0, 1] (importance = 1 - normalized_yake_score)
            max_score = max(score for _, score in raw_keywords)
            if max_score == 0:
                return {kw: 1.0 for kw, _ in raw_keywords[:max_keywords]}

            result = {
                kw.strip(): round(1.0 - (score / max_score), 4)
                for kw, score in raw_keywords[:max_keywords]
                if kw.strip()
            }
            # Sắp xếp giảm dần theo mức quan trọng
            return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))

        except Exception as e:
            print(f'[ERROR] extract_keywords: {e}')
            return {}

    def extract_semantic_embeddings(self, text):
        """
        Trích xuất Content Vector từ văn bản bằng SentenceTransformer.
        Mô hình: paraphrase-multilingual-MiniLM-L12-v2 (hỗ trợ tiếng Việt)
        Output: vector 384 chiều (float list)
        """
        try:
            if not text:
                return []
            # Mã hóa văn bản thành vector ngữ nghĩa 384 chiều
            embedding = self.embedding_model.encode([text], convert_to_numpy=True)[0]
            return embedding.tolist()
        except Exception as e:
            print(f'Error extracting semantic embeddings: {e}')
            return []

    def l2_normalize(self, vector):
        """
        Áp dụng chuẩn hóa L2 (L2 Normalization) cho một vector.
        Đưa vector về độ dài đơn vị (unit norm) trước khi so sánh cosine.

        Args:
            vector (list | np.ndarray): Vector đầu vào cần chuẩn hóa.

        Returns:
            list: Vector đã được chuẩn hóa L2, hoặc [] nếu vector rỗng / norm == 0.
        """
        if not vector:
            return []
        vec = np.array(vector, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm == 0:
            print('[WARNING] L2 norm = 0, không thể chuẩn hóa vector nội dung.')
            return vec.tolist()
        return (vec / norm).tolist()
