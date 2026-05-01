# Tài liệu đính kèm — Mục lục và luồng chạy

Thư mục `docs/` mô tả **đồ án MMDBMS âm thanh**: dữ liệu → đặc trưng → CSDL lai → tìm kiếm → demo.

**Muốn chạy ngay:** cuộn xuống mục **Chạy code (PowerShell)** ngay sau đoạn này — có **lệnh đầy đủ copy-paste**. Phần dưới giải thích **tài liệu nào cho việc gì**, **sinh artifact gì**, **khớp yêu cầu/giai đoạn nào**.

---

## Chạy code (PowerShell)

Mọi lệnh chạy từ **thư mục gốc của repo** (nơi có `requirements.txt`). Giả sử đường dẫn là `ThanhHoa`:

```powershell
cd ThanhHoa
$env:PYTHONIOENCODING = "utf-8"
```

### Cài đặt một lần

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Cần có FFmpeg** trong `PATH`, hoặc đặt biến `FFMPEG_PATH` trỏ tới `ffmpeg.exe`. Lần đầu chạy Whisper / SentenceTransformer / SpeechBrain sẽ **tự tải model** (thường vào `%USERPROFILE%\.cache`).

### Luồng đồ án đầy đủ (khuyến nghị): crawl → Stage 2 → Stage 3 → demo

| Bước | Lệnh | Kết quả (artifact) |
|------|------|---------------------|
| **1 — Stage 1** | `python src/stage1/crawl_audio.py` | WAV dưới `src/Processed_Audio_Data/`, manifest `src/artifacts/stage1/dataset_index.csv` |
| **2 — Stage 2** | Xem khối lệnh ngay dưới | `src/artifacts/stage2/stage2_features.jsonl` |
| **3 — Stage 3** | Xem khối lệnh ngay dưới | `src/artifacts/stage3/audio_hybrid.db`, `content.index`, `voice.index`, `database_build_summary.json`, `requirement3_query_logs.json`, `src/artifacts/stage3/query_logs/` |
| **4 — Demo** | `python src/stage4/demo_cli.py "<đường_tới_file.wav>"` | Hai cột top-3 trên console + `src/artifacts/stage3/demo_last_query.json` (mặc định) |

**Stage 2 — batch đặc trưng:**

```powershell
python src/stage2/batch_feature_extraction.py `
  --input-dir src/Processed_Audio_Data `
  --output-jsonl src/artifacts/stage2/stage2_features.jsonl `
  --whisper-model tiny `
  --stt-max-duration-s 90 `
  --voice-max-duration-s 90
```

**Stage 3 — build CSDL + chạy toàn bộ query trong manifest (`query_seen` / `query_unseen`):**

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

### Không crawl YouTube — chỉ có sẵn file WAV

Đặt WAV đúng cấu trúc dưới `src/Processed_Audio_Data/`, rồi (tuỳ trường hợp) rebuild CSV:

```powershell
python src/stage1/rebuild_dataset_index_from_fs.py --help
```

Sau đó chạy **Stage 2 → Stage 3** như bảng trên.

### Chỉ build DB / FAISS (không chạy batch query)

```powershell
python src/stage3/database_builder.py `
  --stage2-jsonl src/artifacts/stage2/stage2_features.jsonl `
  --manifest-csv src/artifacts/stage1/dataset_index.csv `
  --index-split-role index `
  --sqlite-db src/artifacts/stage3/audio_hybrid.db `
  --content-index src/artifacts/stage3/content.index `
  --voice-index src/artifacts/stage3/voice.index
```

### Truy vấn đúng một file âm thanh + log chi tiết

```powershell
python src/stage3/retrieval_top3.py "src/Processed_Audio_Data/Index/..." `
  --sqlite-db src/artifacts/stage3/audio_hybrid.db `
  --content-index src/artifacts/stage3/content.index `
  --voice-index src/artifacts/stage3/voice.index `
  --top-k 3 `
  --whisper-model tiny `
  --stt-max-duration-s 90 `
  --voice-max-duration-s 90 `
  --output-log src/artifacts/stage3/retrieval_query_log.json
```

### Sửa vài dòng Stage 2 thiếu embedding (tùy chọn)

```powershell
python src/stage2/repair_stage2_records.py --help
```

### Audit tự động Yêu cầu 1–2 (tùy chọn)

```powershell
python src/core/audit_requirements_1_2.py
```

**Lưu ý:** CSV do **`crawl_audio`** sinh **không khớp** schema audit Stage 1 — audit vẫn hữu ích cho **Stage 2** (JSONL). Chi tiết: **`REQ12_COMPLETION.md`**.

### Bash / Linux / macOS

Tương đương: `export PYTHONIOENCODING=utf-8`, kích hoạt venv kiểu `source .venv/bin/activate`, và nối dòng lệnh bằng `\` thay cho `` ` ``.

### Sau khi clone GitHub (repo không chứa WAV / artifact)

Xem thêm **`CLONE_AND_RUN.md`** (`git rm --cached`, `.gitignore`).

---

## 1. Hai luồng triển khai trong repo (quan trọng)

| Luồng | Mục đích | Code chính | Khi nào dùng trong báo cáo |
|--------|-----------|------------|---------------------------|
| **A — Stage 1→4 (SQLite + FAISS)** | Đúng kiến trúc đồ án: manifest crawl, chỉ `index` vào DB, top-3 nội dung/giọng, log cho YC3 | `stage1/crawl_audio.py`, `stage2/batch_feature_extraction.py`, `stage3/database_builder.py`, `stage3/retrieval_top3.py`, `stage3/run_requirement3_pipeline.py`, `stage4/demo_cli.py` | **Khuyến nghị** làm luồng chính cho YC3–4 |
| **B — `src/core/` (MySQL + FAISS)** | Pipeline index/truy vấn kiểu service DB | `core/main.py`, `core/retrieval.py`, `core/evaluate_retrieval.py` | Dùng nếu báo cáo/config đã gắn MySQL; metric formal trong `METRICS_LOGGING_GUIDE` |

Chi tiết cấu trúc code: `src/README_STRUCTURE.md`.

---

## 2. Ánh xạ đề bài → giai đoạn → tài liệu → output

| Yêu cầu / Giai đoạn đề | Ý cần chứng minh | Tài liệu đọc | Chạy gì (luồng A) | Ra cái gì |
|-------------------------|------------------|--------------|-------------------|-----------|
| **GĐ1 / YC1** Chuẩn dữ liệu, ≥500 file*, chủ đề+speaker, tiền xử lý, chỉ mục | CSV manifest + WAV chuẩn | `STAGE1_STATUS.md`, `CLONE_AND_RUN.md` | `python src/stage1/crawl_audio.py` (hoặc copy WAV + `rebuild_dataset_index_from_fs.py`) | `src/Processed_Audio_Data/**`, `src/artifacts/stage1/dataset_index.csv` |
| **GĐ2 / YC2** Thuộc tính nội dung + giọng + lý thuyết | Giải thích chọn thuộc tính & nguyên lý | `STAGE2_STATUS.md`, `src/stage2/Tài_liệu_2.1.md`, `Tài_liệu_2.2.md` | `python src/stage2/batch_feature_extraction.py --input-dir ... --output-jsonl ...` | `src/artifacts/stage2/stage2_features.jsonl` |
| **GĐ3 / YC3** CSDL lai, đổ vector, top-3×2, sơ đồ, log trung gian | SQLite + FAISS, thuật toán cosine/IP | `STAGE3_3a.md`, `STAGE3_3b.md` | `database_builder.py` **hoặc** gộp trong `run_requirement3_pipeline.py` | `audio_hybrid.db`, `content.index`, `voice.index`, `database_build_summary.json` |
| **YC3** Truy vấn một file | Top-3 nội dung + top-3 giọng giảm dần similarity | `STAGE3_3b.md` | `python src/stage3/retrieval_top3.py <.wav> ...` hoặc pipeline | `retrieval_query_log.json` hoặc log trong `query_logs/` |
| **GĐ4 / YC4** Demo seen/unseen + đánh giá | Hai kịch bản query + chứng cứ chạy | `CLONE_AND_RUN.md`, `METRICS_LOGGING_GUIDE.md` | `python src/stage3/run_requirement3_pipeline.py ...`; demo: `python src/stage4/demo_cli.py "<wav>"` | `requirement3_query_logs.json`, `demo_last_query.json` (tuỳ đường dẫn) |

\*Số lượng 500: do crawler + manifest quyết định; kiểm chứng cục bộ: `database_build_summary.json` (`inserted_records`, `content_vectors`).

---

## 3. Danh mục từng file trong `docs/`

| File | Nội dung có trong đó | Ai đọc | Ghi chú chạy / output |
|------|----------------------|--------|------------------------|
| **README.md** (file này) | Mục lục + map yêu cầu + **§ Chạy code (PowerShell)** | Người mới vào repo | Copy-paste lệnh đầy đủ phía trên |
| **CLONE_AND_RUN.md** | Clone nhẹ; không push âm thanh/artifact; tái tạo pipeline | Người clone GitHub | Lệnh PowerShell từng bước A→D; sinh lại toàn bộ artifact |
| **STAGE1_STATUS.md** | Tiêu chí GĐ1 đối chiếu code | YC1 | Hai kiểu CSV có thể có — xem mục "Schema chỉ mục" trong file |
| **STAGE2_STATUS.md** | Tiêu chí GĐ2 + danh mục Stage 2 | YC2 | Trỏ `Tài_liệu_2.1` / `2.2` trong `src/stage2/` |
| **STAGE3_3a.md** | Sơ đồ khối Mermaid, quy trình, **thuật toán Top-3** nội dung/giọng | YC3 phần a | Khớp code `database_builder.py`, `retrieval_top3.py` |
| **STAGE3_3b.md** | Lưu DB, truy vấn, log trung gian (D/I matrix…) | YC3 phần b | Lệnh mẫu + giải thích cosine qua `IndexFlatIP` + L2 |
| **REQ12_COMPLETION.md** | Checklist **YC1–2** + audit tự động | Sau khi có CSV + JSONL | `python src/core/audit_requirements_1_2.py` → `req12_audit.json` |
| **AUDIT_GAP_MATRIX.md** | Ma trận đề bài ↔ hiện trạng (cập nhật theo thời điểm) | Rubric tổng | Không chạy |
| **FAST_TEST_PROTOCOL.md** | Pilot nhỏ trước khi scale | Kiểm thử | Phần lệnh có nhánh **`core/`**; có thể thay pilot bằng luồng Stage 3 tương đương |
| **METRICS_LOGGING_GUIDE.md** | precision@k, latency, file log đánh giá | YC4 | `evaluate_retrieval.py` (**core**); bổ sung log Stage 3 trong file |
| **SCALE_500_CHECKLIST.md** | Gate trước batch lớn | Trước crawl dài | Đã bổ sung bước Stage 3 song song với core |

Luồng **đặt tài liệu học thuật đề phần 2** trực tiếp trong code:

- `src/stage2/Tài_liệu_2.1.md` — lý do + giá trị thông tin thuộc tính  
- `src/stage2/Tài_liệu_2.2.md` — nguyên lý trích xuất  

---

## 4. Luồng khuyến nghị (tóm tắt)

Đã nhập **đầy đủ lệnh** tại mục **Chạy code (PowerShell)** (đầu file). Phần Git / loại file nặng khi push: **`CLONE_AND_RUN.md`**.

1. Stage 1 → WAV + CSV  
2. Stage 2 → JSONL đặc trưng  
3. Stage 3 → SQLite + FAISS + log query  
4. Stage 4 → `demo_cli.py` hai cột  

---

## 5. Audit YC1–2 và giới hạn schema CSV

Script `src/core/audit_requirements_1_2.py` kiểm Stage 1 với CSV có các cột kiểu **`id`, `filename`, `duration_sec`, `status`** (thường do **`stage1/cli.py` / pipeline** sinh).

Manifest do **`crawl_audio.py`** sinh dùng schema **`file_id`, `filepath`, `split_role`, `duration`, …** — **không** khớp audit Stage 1 hiện tại; audit vẫn **hữu ích cho Stage 2** (JSONL + vector). Chi tiết: **`REQ12_COMPLETION.md`**.

---

*Tài liệu trong `docs/` được đồng bộ để người đọc biết **đang có gì**, **chạy sao**, **ra output gì**, và **ứng với yêu cầu/giai đoạn nào**.*
