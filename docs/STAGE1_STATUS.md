# Giai đoạn 1 - Đánh giá đạt/chưa đạt và phần đã hoàn thiện

Tài liệu này đối chiếu trực tiếp các tiêu chí Giai đoạn 1 với hiện trạng code và phần bổ sung mới.

Lưu ý phạm vi: bám đồ án môn học, ưu tiên quy trình đơn giản - dễ hiểu - chạy được. Các kỹ thuật nâng cao được để ở mức tùy chọn.

## Cấu trúc code Giai đoạn 1 (đã tách module)

- `src/stage1/config.py`: tham số CLI + chuẩn dữ liệu.
- `src/stage1/metadata.py`: quét file, suy luận speaker/topic, ghép metadata nguồn.
- `src/stage1/audio_processing.py`: chuẩn hóa wav/16k/mono, trim silence, normalize.
- `src/stage1/pipeline.py`: luồng xử lý + QC + xuất CSV/summary.
- `src/stage1/cli.py`: entrypoint chạy chuẩn bị dữ liệu.
- `src/stage1/crawl_audio.py`: script thu thập dữ liệu thô từ YouTube.

## 1) Tiêu chí: Thống nhất tiêu chuẩn dữ liệu

**Đã làm:**
- Định nghĩa chuẩn kỹ thuật trong `src/stage1/config.py` (`DataStandard`):
  - định dạng cho phép: `.mp3/.wav/.flac/.m4a/.mp4`
  - sample rate chuẩn: `16kHz`
  - mono channel
  - ngưỡng độ dài tối thiểu/tối đa
- Có tham số `label_layout` để đồng bộ cách đọc nhãn thư mục (`speaker_topic` hoặc `topic_speaker`).
- Xuất `dataset_prep_summary.json` để lưu lại chuẩn dùng khi chạy.

**Đánh giá:** Đạt.

## 2) Tiêu chí: Thu thập dữ liệu

**Đã làm:**
- Có script crawl YouTube: `src/stage1/crawl_audio.py`.
- Có metadata nguồn và download archive (`download_archive`).
- Crawler xuất WAV chuẩn và ghi `src/artifacts/stage1/dataset_index.csv` kèm **`split_role`** (`index` / `query_seen` / `query_unseen`) phục vụ YC3–4.

**Mục tiêu ≥500 file (index):**
- Do chính sách crawler (`max-index-per-playlist`, số playlist) và **không** được đẩy lên Git — kiểm chứng cục bộ: đếm dòng `split_role=index` trong CSV hoặc xem `database_build_summary.json` sau Stage 3.

**Đánh giá:** Đạt khi máy chủ đã chạy đủ crawl/pipeline theo đề; repo chỉ chứa **code**, không chứa toàn bộ WAV (xem `docs/CLONE_AND_RUN.md`).

## 3) Tiêu chí: Kiểm duyệt mỗi file có 1 chủ đề và 1 người nói

**Đã làm:**
- Tự suy luận `topic_id`, `speaker_id` từ cấu trúc thư mục.
- Đưa trạng thái `status` (`PASS/FAIL`) và `issues` vào `dataset_index.csv`.

**Lưu ý phản biện:**
- Máy không thể khẳng định 100% "1 người nói/file" nếu không có nhãn hoặc mô hình diarization.
- Cơ chế hiện tại là **gating kiểm duyệt có thể audit**, không phải xác thực tuyệt đối.

**Đánh giá:** Đạt ở mức kiểm duyệt vận hành, chưa đạt xác thực tuyệt đối (cần nhãn/manual review).

## 4) Tiêu chí: Tiền xử lý (trim silence, normalize, denoise)

**Đã làm trong `src/stage1/audio_processing.py` và `src/stage1/pipeline.py`:**
- `trim_silence` bằng `librosa.effects.trim`.
- `denoise` nhẹ bằng spectral subtraction.
- `normalize` peak về mức chuẩn.
- Ghi file chuẩn hóa ra `Processed_Audio_Data` dạng WAV PCM 16-bit.

**Đánh giá:** Đạt.

## 5) Tiêu chí: Lập chỉ mục thống kê file

**Đã làm — hai kiểu CSV có thể tồn tại:**

1. **`cli.py` / `pipeline.py`:** CSV kiểu báo cáo QC với `status`, `duration_sec`, `issues`, … — **khớp** `src/core/audit_requirements_1_2.py` phần Stage 1.
2. **`crawl_audio.py`:** CSV crawler với `file_id`, `filepath`, `playlist_url`, `video_url`, `split_role`, `duration`, … — **phục vụ** Stage 3 (lọc `index`), nhưng **không khớp** audit Stage 1 hiện tại (xem `docs/REQ12_COMPLETION.md`).

**Đánh giá:** Đạt chức năng chỉ mục; khi viết báo cáo cần **nêu rõ đang dùng schema nào**.

## Kết luận Giai đoạn 1

- Chuẩn dữ liệu, crawl, tiền xử lý và chỉ mục đã có đủ module.
- **Luồng báo cáo khuyến nghị:** `docs/README.md` → **`CLONE_AND_RUN.md`** (tái tạo WAV + CSV cục bộ).

---

## Liên kết

- Mục lục tài liệu + map yêu cầu: **`docs/README.md`**
