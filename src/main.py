# -*- coding: utf-8 -*-
"""
main.py
-------
Pipeline xử lý âm thanh và lưu trữ phân tán:
  - Vector (Content 384-dim & Voice 192-dim, đã L2 normalize) → FAISS
  - Transcript, Keywords, Metadata                            → MySQL
"""

import os
import librosa

from voice_feature_extractor import VoiceFeatureExtractor
from content_feature_extractor import ContentFeatureExtractor
from faiss_manager import FaissManager
from db_manager import DatabaseManager


# ── Thư mục chứa dữ liệu âm thanh ────────────────────────────────────────────
AUDIO_DIR = 'Am_Thanh_Data'


# ─────────────────────────────────────────────────────────────────────────────
# Hàm tiện ích
# ─────────────────────────────────────────────────────────────────────────────

def get_audio_duration(audio_path: str) -> float:
    """Đọc và trả về thời lượng (giây) của file âm thanh."""
    try:
        y, sr = librosa.load(audio_path, sr=16000)
        return len(y) / sr
    except Exception as e:
        print(f'[WARN] Không đọc được thời lượng {audio_path}: {e}')
        return 0.0


def make_file_id(filename: str) -> str:
    """Tạo file_id an toàn từ tên file (dùng làm khoá MySQL UNIQUE)."""
    return (filename
            .replace(' ', '_')
            .replace('(', '')
            .replace(')', '')
            .replace('.', '_'))


def collect_audio_files(base_dir: str) -> list:
    """Duyệt đệ quy tìm tất cả file audio (.mp3, .wav, .flac)."""
    audio_files = []
    for root, _, files in os.walk(base_dir):
        for f in files:
            if f.lower().endswith(('.mp3', '.wav', '.flac')):
                audio_files.append(os.path.join(root, f))
    return audio_files


# ─────────────────────────────────────────────────────────────────────────────
# Hàm xử lý một file âm thanh
# ─────────────────────────────────────────────────────────────────────────────

def process_and_store(
    audio_path: str,
    voice_extractor: VoiceFeatureExtractor,
    content_extractor: ContentFeatureExtractor,
    faiss_mgr: FaissManager,
    db_mgr: DatabaseManager,
) -> bool:
    """
    Xử lý một file âm thanh và lưu kết quả vào FAISS + MySQL.

    Luồng:
      1. Trích xuất đặc trưng âm học & Speaker Embedding (ECAPA-TDNN)
      2. Phiên âm Whisper → TF-IDF Keywords → Content Embedding (SentenceTransformer)
      3. Chuẩn hóa L2 cả hai vector
      4. Thêm Content Vector → faiss_content.index  → content_faiss_id
      5. Thêm Voice Vector   → faiss_voice.index    → voice_faiss_id
      6. Lưu metadata + transcript + keywords + faiss_ids → MySQL

    Args:
        audio_path: Đường dẫn đến file âm thanh.
        voice_extractor: Instance VoiceFeatureExtractor.
        content_extractor: Instance ContentFeatureExtractor.
        faiss_mgr: Instance FaissManager.
        db_mgr: Instance DatabaseManager.

    Returns:
        bool: True nếu xử lý thành công.
    """
    filename = os.path.basename(audio_path)
    file_id  = make_file_id(filename)

    # ── Bỏ qua nếu đã tồn tại trong DB ───────────────────────────────────────
    if db_mgr.record_exists(file_id):
        print(f'[SKIP] Đã tồn tại: {filename}')
        return True

    print(f'\n[PROCESS] {filename}')

    # ── Bước 1: Trích xuất đặc trưng âm học & Speaker Embedding ──────────────
    acoustic_features = {}
    raw_voice_vector  = []
    try:
        acoustic_features = voice_extractor.extract_acoustic_features(audio_path)
        raw_voice_vector  = voice_extractor.extract_speaker_embeddings(audio_path)
        print(f'  ✓ Voice features  (Speaker Embedding dim={len(raw_voice_vector)})')
    except Exception as e:
        print(f'  ✗ Voice extraction lỗi: {e}')

    # ── Bước 2: Phiên âm & Trích xuất Content Vector ─────────────────────────
    transcript       = ''
    keywords         = {}
    raw_content_vector = []
    try:
        transcript         = content_extractor.transcribe_audio(audio_path)
        keywords           = content_extractor.extract_keywords(transcript)
        raw_content_vector = content_extractor.extract_semantic_embeddings(transcript)
        print(f'  ✓ Content features (transcript={len(transcript)} ký tự, '
              f'embedding dim={len(raw_content_vector)})')
    except Exception as e:
        print(f'  ✗ Content extraction lỗi: {e}')

    # ── Bước 3: Chuẩn hóa L2 ─────────────────────────────────────────────────
    norm_content_vector = content_extractor.l2_normalize(raw_content_vector)
    norm_voice_vector   = voice_extractor.l2_normalize(raw_voice_vector)
    print(f'  ✓ L2 Normalize  (content dim={len(norm_content_vector)}, '
          f'voice dim={len(norm_voice_vector)})')

    # ── Bước 4 & 5: Lưu vector vào FAISS ─────────────────────────────────────
    content_faiss_id = faiss_mgr.add_content_vector(norm_content_vector)
    voice_faiss_id   = faiss_mgr.add_voice_vector(norm_voice_vector)
    faiss_mgr.save()   # persist ngay sau mỗi file để tránh mất dữ liệu
    print(f'  ✓ FAISS  content_id={content_faiss_id}, voice_id={voice_faiss_id}')

    # ── Bước 6: Lưu metadata & transcript vào MySQL ───────────────────────────
    record = {
        # Định danh
        'file_id':          file_id,
        'filename':         filename,
        'file_path':        os.path.abspath(audio_path),

        # Metadata kỹ thuật
        'duration_seconds': get_audio_duration(audio_path),
        'file_size_bytes':  os.path.getsize(audio_path),

        # Nội dung ngữ nghĩa
        'transcript':       transcript,
        'tfidf_keywords':   keywords,

        # Đặc trưng âm học (từ acoustic_features)
        'mfccs_mean':   acoustic_features.get('mfccs_mean', []),
        'mfccs_std':    acoustic_features.get('mfccs_std', []),
        'pitch_mean':   acoustic_features.get('pitch_mean', 0.0),
        'pitch_std':    acoustic_features.get('pitch_std', 0.0),
        'energy_mean':  acoustic_features.get('energy_mean', 0.0),
        'energy_std':   acoustic_features.get('energy_std', 0.0),
        'zcr_mean':     acoustic_features.get('zcr_mean', 0.0),
        'zcr_std':      acoustic_features.get('zcr_std', 0.0),

        # Liên kết FAISS
        'content_faiss_id': content_faiss_id,
        'voice_faiss_id':   voice_faiss_id,
    }

    db_id = db_mgr.insert_record(record)
    if db_id == -1:
        print(f'  ✗ MySQL insert thất bại cho {filename}')
        return False

    print(f'  ✓ MySQL  record id={db_id}')
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Hàm main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print('=' * 60)
    print('  Hệ thống xử lý âm thanh — FAISS + MySQL Storage')
    print('=' * 60)

    # ── Khởi tạo extractors ───────────────────────────────────────────────────
    print('\n[INIT] Đang khởi tạo các mô hình...')
    voice_extractor   = VoiceFeatureExtractor()
    content_extractor = ContentFeatureExtractor()

    # ── Khởi tạo FAISS & MySQL ────────────────────────────────────────────────
    print('\n[INIT] Đang kết nối FAISS và MySQL...')
    faiss_mgr = FaissManager()
    db_mgr    = DatabaseManager()

    # ── Thu thập danh sách file âm thanh ─────────────────────────────────────
    audio_files = collect_audio_files(AUDIO_DIR)
    print(f'\n[INFO] Tìm thấy {len(audio_files)} file âm thanh trong "{AUDIO_DIR}"')

    if not audio_files:
        print('[WARN] Không tìm thấy file âm thanh nào. Kết thúc.')
        db_mgr.close()
        return

    # ── Xử lý từng file ───────────────────────────────────────────────────────
    success_count = 0
    fail_count    = 0

    for i, audio_path in enumerate(audio_files, start=1):
        print(f'\n[{i}/{len(audio_files)}]', end=' ')
        try:
            ok = process_and_store(
                audio_path,
                voice_extractor,
                content_extractor,
                faiss_mgr,
                db_mgr,
            )
            if ok:
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f'[ERROR] Lỗi không mong muốn với {audio_path}: {e}')
            fail_count += 1

    # ── Tổng kết ──────────────────────────────────────────────────────────────
    print('\n' + '=' * 60)
    print('  KẾT QUẢ XỬ LÝ')
    print('=' * 60)
    print(f'  Tổng file       : {len(audio_files)}')
    print(f'  Thành công      : {success_count}')
    print(f'  Thất bại        : {fail_count}')
    print(f'  Bỏ qua (trùng) : {len(audio_files) - success_count - fail_count}')

    faiss_stats = faiss_mgr.stats()
    print(f'\n  FAISS Content index : {faiss_stats["content_index"]["total_vectors"]} vectors')
    print(f'  FAISS Voice index   : {faiss_stats["voice_index"]["total_vectors"]} vectors')
    print(f'  MySQL records       : {db_mgr.count_records()}')

    db_mgr.close()
    print('\n[DONE] Hoàn tất pipeline lưu trữ.\n')


if __name__ == '__main__':
    main()
