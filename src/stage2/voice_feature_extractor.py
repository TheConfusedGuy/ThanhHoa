# -*- coding: utf-8 -*-
"""
Stage 2 - Voice feature extractor
---------------------------------
Rang buoc pham vi:
- Dung librosa de trich xuat MFCC, Pitch, Energy, ZCR
- Dung speechbrain ECAPA-TDNN de tao speaker embedding
- Khong trich xuat Mel-spectrogram, khong trich xuat x-vector
"""

from __future__ import annotations

from typing import Dict, List

import librosa
import numpy as np
import torch
import torchaudio


class VoiceFeatureExtractor:
    """
    Trich xuat dac trung giong noi phuc vu speaker retrieval.
    """

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._ecapa_model = None

    def extract_acoustic_features(self, audio_path: str) -> Dict[str, object]:
        """
        Trich xuat:
        - MFCC (mean, std)
        - Pitch (mean, std)
        - Energy RMS (mean, std)
        - ZCR (mean, std)
        """
        y, sr = librosa.load(audio_path, sr=self.sample_rate)

        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfccs_mean = np.mean(mfccs, axis=1)
        mfccs_std = np.std(mfccs, axis=1)

        pitches, _ = librosa.piptrack(y=y, sr=sr)
        valid_pitch = pitches[pitches > 0]
        pitch_mean = float(np.mean(valid_pitch)) if valid_pitch.size else 0.0
        pitch_std = float(np.std(valid_pitch)) if valid_pitch.size else 0.0

        rms = librosa.feature.rms(y=y)
        energy_mean = float(np.mean(rms))
        energy_std = float(np.std(rms))

        zcr = librosa.feature.zero_crossing_rate(y)
        zcr_mean = float(np.mean(zcr))
        zcr_std = float(np.std(zcr))

        return {
            "mfccs_mean": mfccs_mean.tolist(),
            "mfccs_std": mfccs_std.tolist(),
            "pitch_mean": pitch_mean,
            "pitch_std": pitch_std,
            "energy_mean": energy_mean,
            "energy_std": energy_std,
            "zcr_mean": zcr_mean,
            "zcr_std": zcr_std,
        }

    def _load_ecapa_model(self):
        if self._ecapa_model is None:
            from speechbrain.inference.speaker import EncoderClassifier

            print("[Stage2][Voice] Loading ECAPA-TDNN model...")
            self._ecapa_model = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir="pretrained_models/spkrec-ecapa-voxceleb",
                run_opts={"device": "cuda" if torch.cuda.is_available() else "cpu"},
            )
        return self._ecapa_model

    def extract_speaker_embeddings(self, audio_path: str) -> List[float]:
        """
        Trich xuat speaker embedding 192-d tu ECAPA-TDNN.
        """
        try:
            model = self._load_ecapa_model()
            waveform, sr = torchaudio.load(audio_path)

            if sr != self.sample_rate:
                resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=self.sample_rate)
                waveform = resampler(waveform)
            if waveform.shape[0] > 1:
                waveform = waveform.mean(dim=0, keepdim=True)

            with torch.no_grad():
                embeddings = model.encode_batch(waveform)
            vector = embeddings.squeeze().cpu().numpy().tolist()
            return vector if isinstance(vector, list) else [float(vector)]
        except Exception as exc:
            print(f"[Stage2][Voice][ERROR] extract_speaker_embeddings: {audio_path} -> {exc}")
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

