# -*- coding: utf-8 -*-
import librosa
import numpy as np
import torch
import torchaudio

class VoiceFeatureExtractor:
    """
    Lớp để trích xuất các đặc trưng âm thanh cho việc nhận dạng giọng nói/người nói.
    Tich hợp mô hình ECAPA-TDNN (SpeechBrain) để tạo Speaker Embedding.
    """

    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self._ecapa_model = None  # Lazy loading - chỉ tải khi cần

    def extract_acoustic_features(self, audio_path):
        """
        Trích xuất các đặc trưng âm thanh cơ bản: MFCCs, Pitch, Energy, Zero Crossing Rate.

        Args:
            audio_path (str): Đường dẫn đến tệp âm thanh.

        Returns:
            dict: Từ điển chứa các đặc trưng đã trích xuất.
        """
        # Tải âm thanh
        y, sr = librosa.load(audio_path, sr=self.sample_rate)

        # MFCCs (Mel-frequency cepstral coefficients)
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfccs_mean = np.mean(mfccs, axis=1)
        mfccs_std = np.std(mfccs, axis=1)

        # Pitch (Tần số cơ bản)
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitch_mean = np.mean(pitches[pitches > 0]) if np.any(pitches > 0) else 0
        pitch_std = np.std(pitches[pitches > 0]) if np.any(pitches > 0) else 0

        # Energy (Root Mean Square)
        rms = librosa.feature.rms(y=y)
        energy_mean = np.mean(rms)
        energy_std = np.std(rms)

        # Zero Crossing Rate
        zcr = librosa.feature.zero_crossing_rate(y)
        zcr_mean = np.mean(zcr)
        zcr_std = np.std(zcr)

        return {
            "mfccs_mean": mfccs_mean.tolist(),
            "mfccs_std": mfccs_std.tolist(),
            "pitch_mean": float(pitch_mean),
            "pitch_std": float(pitch_std),
            "energy_mean": float(energy_mean),
            "energy_std": float(energy_std),
            "zcr_mean": float(zcr_mean),
            "zcr_std": float(zcr_std)
        }

    def _load_ecapa_model(self):
        """
        Lazy-load mô hình ECAPA-TDNN từ SpeechBrain.
        Mô hình: speechbrain/spkrec-ecapa-voxceleb - được pretrained trên VoxCeleb.
        """
        if self._ecapa_model is None:
            from speechbrain.inference.speaker import EncoderClassifier
            print('[INFO] Đang tải mô hình ECAPA-TDNN (speechbrain/spkrec-ecapa-voxceleb)...')
            self._ecapa_model = EncoderClassifier.from_hparams(
                source='speechbrain/spkrec-ecapa-voxceleb',
                savedir='pretrained_models/spkrec-ecapa-voxceleb',
                run_opts={'device': 'cuda' if torch.cuda.is_available() else 'cpu'}
            )
            print('[INFO] Mô hình ECAPA-TDNN đã sẵn sàng.')
        return self._ecapa_model

    def extract_speaker_embeddings(self, audio_path):
        """
        Trích xuất Voice Vector (Speaker Embedding) bằng mô hình ECAPA-TDNN.

        Mô hình ECAPA-TDNN (Emphasized Channel Attention, Propagation and Aggregation
        - Time Delay Neural Network) được pretrained trên VoxCeleb, tạo ra vector
        192 chiều đặc trưng cho giọng nói của một người.

        Args:
            audio_path (str): Đường dẫn đến tệp âm thanh (.mp3 hoặc .wav).

        Returns:
            list: Vector 192 chiều (float list) đại diện giọng nói,
                  hoặc [] nếu xảy ra lỗi.
        """
        try:
            model = self._load_ecapa_model()

            # Đọc và chuẩn hóa âm thanh về 16kHz mono
            waveform, sr = torchaudio.load(audio_path)
            if sr != 16000:
                resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=16000)
                waveform = resampler(waveform)
            # Đảm bảo mono (1 kênh)
            if waveform.shape[0] > 1:
                waveform = waveform.mean(dim=0, keepdim=True)

            # Trích xuất embedding qua ECAPA-TDNN (output shape: [1, 1, 192])
            with torch.no_grad():
                embeddings = model.encode_batch(waveform)

            # Flatten về 1D list 192 phần tử
            embedding_vector = embeddings.squeeze().cpu().numpy().tolist()
            # Nếu đầu ra vẫn là scalar thì bọc trong list
            if isinstance(embedding_vector, float):
                embedding_vector = [embedding_vector]
            return embedding_vector

        except Exception as e:
            print(f'[ERROR] Không thể trích xuất Speaker Embedding từ {audio_path}: {e}')
            return []

    def l2_normalize(self, vector):
        """
        Áp dụng chuẩn hóa L2 (L2 Normalization) cho một Speaker Embedding vector.
        Đưa vector về độ dài đơn vị (unit norm) giúp so sánh cosine similarity
        giữa các giọng nói chính xác hơn.

        Args:
            vector (list | np.ndarray): Speaker Embedding vector cần chuẩn hóa.

        Returns:
            list: Vector đã được chuẩn hóa L2, hoặc [] nếu vector rỗng / norm == 0.
        """
        if not vector:
            return []
        vec = np.array(vector, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm == 0:
            print('[WARNING] L2 norm = 0, không thể chuẩn hóa Speaker Embedding.')
            return vec.tolist()
        return (vec / norm).tolist()


# Ví dụ sử dụng
if __name__ == '__main__':
    extractor = VoiceFeatureExtractor()
    # Thay thế bằng đường dẫn thực tế
    audio_path = 'Am_Thanh_Data/ĐỐI NHÂN XỬ THẾ/10 bài học giao tiếp ứng xử nâng cấp giá trị của bạn.mp3'
    try:
        features = extractor.extract_acoustic_features(audio_path)
        embeddings = extractor.extract_speaker_embeddings(audio_path)
        embeddings_normalized = extractor.l2_normalize(embeddings)
        print('Đặc trưng âm thanh:', features)
        print('Kích thước Speaker Embedding (ECAPA-TDNN):', len(embeddings))
        print('Kích thước sau L2 Normalize:', len(embeddings_normalized))
    except Exception as e:
        print(f'Error: {e}')
