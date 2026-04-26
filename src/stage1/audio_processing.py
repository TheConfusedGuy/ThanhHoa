# -*- coding: utf-8 -*-
"""Hàm tiền xử lý âm thanh cho Giai đoạn 1."""

from pathlib import Path
from typing import Tuple

import librosa
import numpy as np
import soundfile as sf

from .config import DataStandard


def denoise_spectral_subtract(y: np.ndarray, sr: int, strength: float = 1.5) -> np.ndarray:
    if y.size == 0:
        return y
    n_fft = 1024
    hop = 256
    stft = librosa.stft(y, n_fft=n_fft, hop_length=hop)
    mag = np.abs(stft)
    phase = np.exp(1j * np.angle(stft))
    noise_frames = max(1, int(0.25 * sr / hop))
    noise_profile = np.median(mag[:, :noise_frames], axis=1, keepdims=True)
    mag_clean = np.maximum(mag - (strength * noise_profile), 0.0)
    y_clean = librosa.istft(mag_clean * phase, hop_length=hop, length=len(y))
    return y_clean.astype(np.float32)


def peak_normalize(y: np.ndarray, target_db: float = -1.0) -> np.ndarray:
    if y.size == 0:
        return y
    peak = float(np.max(np.abs(y)))
    if peak <= 1e-8:
        return y
    target_amp = 10 ** (target_db / 20.0)
    scale = target_amp / peak
    y_norm = np.clip(y * scale, -1.0, 1.0)
    return y_norm.astype(np.float32)


def preprocess_audio(audio_path: Path, std: DataStandard) -> Tuple[np.ndarray, int, dict]:
    """
    Quy trình cốt lõi đúng phạm vi môn học:
      1) Resample + mono
      2) Trim silence đầu/cuối
      3) Normalize âm lượng
    """
    y, sr = librosa.load(str(audio_path), sr=std.target_sample_rate, mono=std.mono)
    original_duration = float(len(y) / sr) if sr else 0.0

    y_trim, _ = librosa.effects.trim(y, top_db=std.trim_silence_top_db)
    y_work = y_trim
    if std.enable_denoise:
        y_work = denoise_spectral_subtract(y_work, sr, strength=std.denoise_strength)
    y_norm = peak_normalize(y_work, target_db=std.peak_target_db)

    processed_duration = float(len(y_norm) / sr) if sr else 0.0
    meta = {
        "original_duration_s": round(original_duration, 3),
        "processed_duration_s": round(processed_duration, 3),
        "sample_rate": sr,
    }
    return y_norm, sr, meta


def ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def write_wav_mirror(input_dir: Path, output_dir: Path, src_path: Path, y: np.ndarray, sr: int) -> Path:
    rel = src_path.relative_to(input_dir)
    dst = (output_dir / rel).with_suffix(".wav")
    ensure_parent(dst)
    sf.write(str(dst), y, sr, subtype="PCM_16")
    return dst


def write_rejected_mirror(input_dir: Path, rejected_dir: Path, src_path: Path) -> Path:
    rel = src_path.relative_to(input_dir)
    dst = rejected_dir / rel
    ensure_parent(dst)
    # copy bằng stream để tránh phụ thuộc shutil copy2 metadata trên một số môi trường
    with open(src_path, "rb") as f_in, open(dst, "wb") as f_out:
        f_out.write(f_in.read())
    return dst
