# -*- coding: utf-8 -*-
"""Core indexing pipeline: Stage2 features -> FAISS + MySQL."""

import os
import librosa

try:
    from stage2.voice_feature_extractor import VoiceFeatureExtractor
    from stage2.content_feature_extractor import ContentFeatureExtractor
    from core.faiss_manager import FaissManager
    from core.db_manager import DatabaseManager
except ImportError:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from stage2.voice_feature_extractor import VoiceFeatureExtractor
    from stage2.content_feature_extractor import ContentFeatureExtractor
    from core.faiss_manager import FaissManager
    from core.db_manager import DatabaseManager


def _resolve_audio_dir() -> str:
    env_value = os.getenv("AUDIO_DIR", "").strip()
    if env_value:
        return env_value
    for candidate in ("src/Processed_Audio_Data", "Processed_Audio_Data", "src/Am_Thanh_Data", "Am_Thanh_Data"):
        if os.path.exists(candidate):
            return candidate
    return "src/Processed_Audio_Data"


AUDIO_DIR = _resolve_audio_dir()
BATCH_SAVE_INTERVAL = int(os.getenv("FAISS_SAVE_INTERVAL", "20"))


def get_audio_duration(audio_path: str) -> float:
    try:
        y, sr = librosa.load(audio_path, sr=16000)
        return len(y) / sr
    except Exception as e:
        print(f"[WARN] Không đọc được thời lượng {audio_path}: {e}")
        return 0.0


def make_file_id(filename: str) -> str:
    return filename.replace(" ", "_").replace("(", "").replace(")", "").replace(".", "_")


def collect_audio_files(base_dir: str) -> list:
    audio_files = []
    for root, _, files in os.walk(base_dir):
        for f in files:
            if f.lower().endswith((".mp3", ".wav", ".flac", ".m4a", ".mp4")):
                audio_files.append(os.path.join(root, f))
    return audio_files


def process_and_store(audio_path: str, voice_extractor, content_extractor, faiss_mgr, db_mgr, persist_faiss_now: bool = False) -> bool:
    filename = os.path.basename(audio_path)
    file_id = make_file_id(filename)
    if db_mgr.record_exists(file_id):
        print(f"[SKIP] Đã tồn tại: {filename}")
        return True

    print(f"\n[PROCESS] {filename}")
    acoustic_features = {}
    raw_voice_vector = []
    try:
        acoustic_features = voice_extractor.extract_acoustic_features(audio_path)
        raw_voice_vector = voice_extractor.extract_speaker_embeddings(audio_path)
    except Exception as e:
        print(f"  ✗ Voice extraction lỗi: {e}")

    transcript = ""
    keywords = {}
    raw_content_vector = []
    try:
        transcript = content_extractor.transcribe_audio(audio_path)
        keywords = content_extractor.extract_keywords(transcript)
        raw_content_vector = content_extractor.extract_semantic_embeddings(transcript)
    except Exception as e:
        print(f"  ✗ Content extraction lỗi: {e}")

    norm_content_vector = content_extractor.l2_normalize(raw_content_vector)
    norm_voice_vector = voice_extractor.l2_normalize(raw_voice_vector)

    content_faiss_id = faiss_mgr.add_content_vector(norm_content_vector)
    voice_faiss_id = faiss_mgr.add_voice_vector(norm_voice_vector)
    if persist_faiss_now:
        faiss_mgr.save()

    record = {
        "file_id": file_id,
        "filename": filename,
        "file_path": os.path.abspath(audio_path),
        "duration_seconds": get_audio_duration(audio_path),
        "file_size_bytes": os.path.getsize(audio_path),
        "transcript": transcript,
        "tfidf_keywords": keywords,  # giữ tên cột DB cũ để tương thích
        "mfccs_mean": acoustic_features.get("mfccs_mean", []),
        "mfccs_std": acoustic_features.get("mfccs_std", []),
        "pitch_mean": acoustic_features.get("pitch_mean", 0.0),
        "pitch_std": acoustic_features.get("pitch_std", 0.0),
        "energy_mean": acoustic_features.get("energy_mean", 0.0),
        "energy_std": acoustic_features.get("energy_std", 0.0),
        "zcr_mean": acoustic_features.get("zcr_mean", 0.0),
        "zcr_std": acoustic_features.get("zcr_std", 0.0),
        "content_faiss_id": content_faiss_id,
        "voice_faiss_id": voice_faiss_id,
    }

    db_id = db_mgr.insert_record(record)
    if db_id == -1:
        print(f"  ✗ MySQL insert thất bại cho {filename}")
        return False
    return True


def main():
    print("=" * 60)
    print("  Core Pipeline — FAISS + MySQL")
    print("=" * 60)

    voice_extractor = VoiceFeatureExtractor()
    content_extractor = ContentFeatureExtractor()
    faiss_mgr = FaissManager()
    db_mgr = DatabaseManager()

    audio_files = collect_audio_files(AUDIO_DIR)
    print(f'\n[INFO] Tìm thấy {len(audio_files)} file âm thanh trong "{AUDIO_DIR}"')
    if not audio_files:
        print("[WARN] Không tìm thấy file âm thanh nào. Kết thúc.")
        db_mgr.close()
        return

    success_count = 0
    fail_count = 0
    since_last_save = 0

    for i, audio_path in enumerate(audio_files, start=1):
        print(f"\n[{i}/{len(audio_files)}]", end=" ")
        try:
            ok = process_and_store(
                audio_path,
                voice_extractor,
                content_extractor,
                faiss_mgr,
                db_mgr,
                persist_faiss_now=False,
            )
            if ok:
                success_count += 1
                since_last_save += 1
                if since_last_save >= max(1, BATCH_SAVE_INTERVAL):
                    faiss_mgr.save()
                    since_last_save = 0
            else:
                fail_count += 1
        except Exception as e:
            print(f"[ERROR] Lỗi không mong muốn với {audio_path}: {e}")
            fail_count += 1

    if since_last_save > 0:
        faiss_mgr.save()

    print("\n" + "=" * 60)
    print("  KẾT QUẢ XỬ LÝ")
    print("=" * 60)
    print(f"  Tổng file       : {len(audio_files)}")
    print(f"  Thành công      : {success_count}")
    print(f"  Thất bại        : {fail_count}")
    print(f"  Bỏ qua (trùng) : {len(audio_files) - success_count - fail_count}")

    faiss_stats = faiss_mgr.stats()
    print(f'\n  FAISS Content index : {faiss_stats["content_index"]["total_vectors"]} vectors')
    print(f'  FAISS Voice index   : {faiss_stats["voice_index"]["total_vectors"]} vectors')
    print(f"  MySQL records       : {db_mgr.count_records()}")
    db_mgr.close()
    print("\n[DONE] Hoàn tất pipeline lưu trữ.\n")


if __name__ == "__main__":
    main()

