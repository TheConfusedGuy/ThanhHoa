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
- Có metadata nguồn và download archive.
- Crawler đã xuất theo cấu trúc mặc định `speaker/topic/file` để khớp parser nhãn của Stage 1.

**Chưa làm đủ theo đề (500 file):**
- Chưa chốt đủ số lượng 500 ở giai đoạn hiện tại (theo yêu cầu tạm hoãn).

**Đánh giá:** Đạt một phần (đã có cơ chế thu thập, chưa đạt số lượng mục tiêu).

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

**Đã làm:**
- Tạo `dataset_index.csv` chứa:
  - `file_id`, `filename`, `source_path`, `processed_file_path`
  - `source_url`
  - `speaker_id`, `topic_id`
  - thông số kỹ thuật (`sample_rate`, `duration_sec`)
  - trạng thái và lỗi QC (`status`, `issues`)
- Tạo `dataset_prep_summary.json` tổng hợp `pass_count`, `fail_count`,
  `unknown_topic_count`, `unknown_speaker_count`, `pass_rate`.

**Đánh giá:** Đạt.

## Kết luận Giai đoạn 1 (không tính ràng buộc 500 file)

- Các tiêu chí kỹ thuật cốt lõi của Giai đoạn 1 đã được hoàn thiện.
- Phần còn lại để "đạt tuyệt đối theo đề" là:
  1) mở rộng số lượng dữ liệu lên >= 500 file,
  2) hoàn thiện kiểm duyệt nhãn speaker/topic cho các file đang `REVIEW`.
