# ThanhHoa — MMDBMS âm thanh (chuẩn bị dữ liệu → đặc trưng → CSDL lai → tìm kiếm)

Đồ án xây dựng hệ **cơ sở dữ liệu lưu trữ và tìm kiếm nội dung file âm thanh**: metadata (SQLite) + vector (FAISS), trả **top-3 giống nội dung** và **top-3 giống giọng**.

## Đọc thêm (tài liệu trong repo)

→ **`docs/README.md`** — mục lục, map yêu cầu đề / giai đoạn, lệnh phụ (`database_builder`, `retrieval_top3.py`, audit…).  
→ **`docs/CLONE_AND_RUN.md`** — clone nhẹ, không commit WAV/artifact, tái tạo pipeline.

## Cấu trúc code

→ **`src/README_STRUCTURE.md`**

## Chạy code (PowerShell) — copy-paste

Terminal đặt tại **thư mục gốc repo** (nơi có `requirements.txt`). Bản đầy đủ + giải thích từng bước: **`docs/README.md`**.

```powershell
cd ThanhHoa
$env:PYTHONIOENCODING = "utf-8"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Stage 1 — crawl YouTube → WAV + manifest**

```powershell
python src/stage1/crawl_audio.py
```

**Stage 2 — trích đặc trưng → JSONL**

```powershell
python src/stage2/batch_feature_extraction.py `
  --input-dir src/Processed_Audio_Data `
  --output-jsonl src/artifacts/stage2/stage2_features.jsonl `
  --whisper-model tiny `
  --stt-max-duration-s 90 `
  --voice-max-duration-s 90
```

**Stage 3 — SQLite + FAISS + chạy query seen/unseen + log**

```powershell
python src/stage3/run_requirement3_pipeline.py `
  --stage2-jsonl src/artifacts/stage2/stage2_features.jsonl `
  --manifest-csv src/artifacts/stage1/dataset_index.csv `
  --sqlite-db src/artifacts/stage3/audio_hybrid.db `
  --content-index src/artifacts/stage3/content.index `
  --voice-index src/artifacts/stage3/voice.index `
  --whisper-model tiny `
  --stt-max-duration-s 90 `
  --voice-max-duration-s 90
```

**Stage 4 — demo hai cột top-3** (đổi đường dẫn `.wav` cho đúng máy bạn)

```powershell
python src/stage4/demo_cli.py "src/Processed_Audio_Data/Test_Seen/PhatGiao/SuThanhMinh/B2t3q5bbx4M.wav"
```

*(Đường dẫn trên là ví dụ — sau crawl hãy chọn một `.wav` có trên máy bạn, ví dụ một dòng `filepath` trong `dataset_index.csv`.)*

Cần **FFmpeg**. Sau khi clone mà không có dữ liệu: **`docs/CLONE_AND_RUN.md`**.
