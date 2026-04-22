# -*- coding: utf-8 -*-
import whisper
import soundfile as sf
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
# from sentence_transformers import SentenceTransformer  # Temporarily disabled
import tempfile
import os

class ContentFeatureExtractor:
    def __init__(self):
        print('Loading Whisper model...')
        self.whisper_model = whisper.load_model('base')
        # self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')  # Temporarily disabled
        self.tfidf_vectorizer = TfidfVectorizer(max_features=100, stop_words='english')

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

    def extract_tfidf_keywords(self, text):
        try:
            if not text:
                return {}
            tfidf_matrix = self.tfidf_vectorizer.fit_transform([text])
            feature_names = self.tfidf_vectorizer.get_feature_names_out()
            scores = tfidf_matrix.toarray()[0]
            keywords = {feature_names[i]: float(scores[i]) for i in scores.argsort()[-10:][::-1] if scores[i] > 0}
            return keywords
        except Exception as e:
            print(f'Error extracting TF-IDF: {e}')
            return {}

    def extract_semantic_embeddings(self, text):
        try:
            if not text:
                return []
            # Temporarily return empty list
            # embeddings = self.embedding_model.encode([text])[0]
            # return embeddings.tolist()
            return []
        except Exception as e:
            print(f'Error extracting embeddings: {e}')
            return []
