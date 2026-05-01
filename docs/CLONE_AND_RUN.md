# Sau khi clone: bỏ file nặng trên Git, người pull tự chạy lại

**Mục lục:** `docs/README.md` · **Hướng dẫn chạy copy-paste (đầy đủ):** cùng file `docs/README.md`, mục **Chạy code (PowerShell)**.

## 1. Những gì **không** có trên repo (cố ý)

| Loại | Đường dẫn / mẫu | Cách có lại |
|------|-----------------|-------------|
| Âm thanh đã crawl / đã xử lý | `src/Processed_Audio_Data/`, `src/Am_Thanh_Data/` | Chạy crawler Stage 1 hoặc copy ZIP từ nơi khác vào đúng cấu trúc |
| Artifact pipeline | `src/artifacts/**` (CSV index, JSONL Stage 2, `.db`, `.index`, log…) | Chạy lại Stage 2 → Stage 3 |
| Model đã tải về | Thường nằm ở `%USERPROFILE%\.cache` (Hugging Face, torch…) | Lần đầu chạy script sẽ tự tải |

Quy tắc nằm trong `.gitignore` ở root repo.

## 2. Nếu trước đây đã `git add` nhầm file nặng

Chỉ **gỡ khỏi Git**, file vẫn ở máy bạn:

```powershell
cd E:\THANHHOADPT\ThanhHoa
git rm -r --cached src/Processed_Audio_Data src/Am_Thanh_Data 2>$null
git rm -r --cached src/artifacts 2>$null
git add .gitignore
git commit -m "Stop tracking large audio and artifacts; rely on local regeneration"
```

Sau đó push. Người clone sẽ không kéo các blob đó (và lịch sử cũ vẫn chứa nếu đã từng commit — muốn xóa hẳn khỏi lịch sử cần `git filter-repo` hoặc repo mới).

## 3. Điều kiện môi trường

- Python 3.10+ (khuyến nghị 3.12 như máy đã chạy).
- **FFmpeg** trong `PATH` hoặc biến môi trường `FFMPEG_PATH` (crawler + xử lý âm thanh).
- Cài dependency:

```powershell
cd E:\THANHHOADPT\ThanhHoa
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 4. Luồng tái tạo đầy đủ (crawl → đặc trưng → DB → demo)

Chạy từ **thư mục root** của repo (`ThanhHoa`). Trên PowerShell nên có `$env:PYTHONIOENCODING='utf-8'` nếu đường dẫn có ký tự Unicode.

### Bước A — Thu âm + manifest (Stage 1)

```powershell
python src/stage1/crawl_audio.py
```

Tạo WAV dưới `src/Processed_Audio_Data/` và cập nhật `src/artifacts/stage1/dataset_index.csv` (artifact được sinh cục bộ; không push).

*Nếu không crawl được YouTube,* đặt bộ WAV **đúng cấu trúc thư mục** vào `src/Processed_Audio_Data/` rồi có thể rebuild CSV:

```powershell
python src/stage1/rebuild_dataset_index_from_fs.py
```
(tham số cụ thể xem `--help` của script.)

### Bước B — Trích đặc trưng (Stage 2)

```powershell
python src/stage2/batch_feature_extraction.py `
  --input-dir src/Processed_Audio_Data `
  --output-jsonl src/artifacts/stage2/stage2_features.jsonl `
  --whisper-model tiny `
  --stt-max-duration-s 90 `
  --voice-max-duration-s 90
```

*Nếu vài file thiếu embedding nội dung:* xem `src/stage2/repair_stage2_records.py --help`.

### Bước C — Build DB + chạy query mẫu + log (Stage 3)

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

### Bước D — Demo CLI hai cột (Stage 4)

Chọn một đường dẫn `.wav` có trong `dataset_index.csv` (nhánh query):

```powershell
python src/stage4/demo_cli.py "src/Processed_Audio_Data/Test_Seen/..."
```

## 5. Kiểm tra nhanh Yêu cầu 1–2 (tùy chọn)

```powershell
python src/core/audit_requirements_1_2.py
```

---

**Tóm lại:** Repo chỉ giữ **code + docs + `.gitignore`**. Dữ liệu nặng và artifact là **sản phẩm chạy pipeline trên máy từng người**, không đẩy GitHub để clone nhẹ và đúng tinh thần “reproducible research”.
