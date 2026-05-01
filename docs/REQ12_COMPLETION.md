# Hoàn thiện Yêu cầu 1 và 2 — Checklist và audit

Tài liệu này chốt **chạy đúng** cho:

- **YC1:** Bộ dữ liệu + nhãn chủ đề/người nói + chuẩn hóa (theo pipeline bạn chọn).
- **YC2:** Đặc trưng nội dung + giọng + định dạng vector đúng chiều.

**Luồng đồ án đầy đủ (YC3–4):** xem **`docs/README.md`** và **`docs/CLONE_AND_RUN.md`**.

---

## 1) Hai kiểu chỉ mục Stage 1 (đọc trước khi audit)

| Nguồn CSV | Script sinh ra | Đặc điểm | Dùng cho YC3 crawl split |
|-----------|----------------|----------|---------------------------|
| **Pipeline chuẩn bị** | `python src/stage1/cli.py ...` | Cột kiểu `id`, `filename`, `speaker_id`, `topic_id`, `duration_sec`, `status`, … | Không có `split_role` mặc định |
| **Crawler YouTube** | `python src/stage1/crawl_audio.py` | Cột `file_id`, `filepath`, `split_role`, `duration`, `topic_id`, `speaker_id`, … | Có **`index` / `query_seen` / `query_unseen`** |

---

## 2) Artifact cần có để kiểm YC2 (và một phần YC1)

- **`src/artifacts/stage2/stage2_features.jsonl`** — luôn cần cho Stage 3 và audit Stage 2.

**CSV Stage 1:**

- Nếu dùng **pipeline `cli.py`:** có `src/artifacts/stage1/dataset_index.csv` (hoặc đường dẫn tương đương) **đúng schema audit** → chạy audit đầy đủ YC1+YC2.
- Nếu chỉ dùng **`crawl_audio.py`:** CSV crawler **không khớp** schema `audit_requirements_1_2.py` phần Stage 1 → audit sẽ báo **thiếu cột / FAIL Stage 1**; **vẫn nên tin audit phần Stage 2** (JSONL).

---

## 3) Sinh artifact nếu chưa có

### Cách A — Đã có âm thanh dưới `Processed_Audio_Data/` (thường sau crawl)

```bash
python src/stage2/batch_feature_extraction.py ^
  --input-dir src/Processed_Audio_Data ^
  --output-jsonl src/artifacts/stage2/stage2_features.jsonl ^
  --whisper-model tiny ^
  --stt-max-duration-s 90 ^
  --voice-max-duration-s 90
```

*(PowerShell dùng dấu `` ` `` thay `^`.)*

### Cách B — Chuẩn bị lại qua pipeline Stage 1 (CSV khớp audit)

```bash
python src/stage1/cli.py --input-dir src/Processed_Audio_Data --output-dir src/artifacts/stage1/reprocessed_audio
python src/stage2/batch_feature_extraction.py --input-dir src/Processed_Audio_Data --output-jsonl src/artifacts/stage2/stage2_features.jsonl
```

### Sửa vài dòng JSONL thiếu embedding nội dung (tùy chọn)

```bash
python src/stage2/repair_stage2_records.py --help
```

---

## 4) Audit tự động Yêu cầu 1–2

```bash
python src/core/audit_requirements_1_2.py
```

Tham số (tuỳ đường dẫn):

```bash
python src/core/audit_requirements_1_2.py ^
  --stage1-index-csv src/artifacts/stage1/dataset_index.csv ^
  --stage2-jsonl src/artifacts/stage2/stage2_features.jsonl ^
  --output-json src/artifacts/req12_audit.json
```

**Output:**

- Console: báo cáo PASS/FAIL.
- File: `src/artifacts/req12_audit.json`.

---

## 5) Điều kiện PASS (theo logic script)

### Yêu cầu 1 (Stage 1 trong audit)

- CSV có đủ cột: `id`, `filename`, `speaker_id`, `topic_id`, `duration_sec`, `status`.
- Mỗi dòng `status=PASS`, không `unknown` topic/speaker, duration trong ngưỡng min/max của audit.

### Yêu cầu 2 (Stage 2)

- JSONL không rỗng.
- Mỗi record: `transcript` không rỗng, `content_embedding` đúng **384** chiều, `speaker_embedding` đúng **192** chiều.
- `acoustic_features` có đủ khóa MFCC/Pitch/Energy/ZCR (mean/std).

---

## 6) Phạm vi

- Script **không** kiểm ràng buộc **≥500 file** (có thể bổ sung thủ công trong báo cáo).
- **YC3–4** không thuộc file audit này — xem **`run_requirement3_pipeline.py`** và **`docs/STAGE3_3*.md`**.
