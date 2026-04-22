# -*- coding: utf-8 -*-
import librosa
import numpy as np

class VoiceFeatureExtractor:
    """
    Lớp để trích xuất các đặc trưng âm thanh cho việc nhận dạng giọng nói/người nói.
    """

    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate

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

    def extract_speaker_embeddings(self, audio_path):
        """
        Placeholder for speaker embeddings - requires additional setup.
        """
        return []

# Ví dụ sử dụng
if __name__ == "__main__":
    extractor = VoiceFeatureExtractor()
    # Thay thế bằng đường dẫn thực tế
    audio_path = "Am_Thanh_Data/ĐỐI NHÂN XỬ THẾ/10 bài học giao tiếp ứng xử nâng cấp giá trị của bạn.mp3"
    try:
        features = extractor.extract_acoustic_features(audio_path)
        embeddings = extractor.extract_speaker_embeddings(audio_path)
        print("Đặc trưng âm thanh:", features)
        print("Kích thước embedding người nói:", len(embeddings))
    except Exception as e:
        print(f"Error: {e}")
