# Protocol test nhanh (30-80 file) trước khi scale 500

> **Định hướng hiện tại:** Luồng báo cáo chính dùng **Stage 3** (SQLite + FAISS): xem **`docs/README.md`** và **`docs/CLONE_AND_RUN.md`**.  
> Phần dưới đây mô tả pilot qua **`src/core/`** (MySQL + `retrieval.py`) — vẫn hữu ích nếu bạn giữ nhánh đánh giá `evaluate_retrieval.py`; có thể **mirror** ý tưởng split seen/unseen bằng `dataset_index.csv` của crawler.

## 1) Quy mô đề xuất

- **Dataset pilot**: 30-80 file.
- **Số chủ đề**: 6-10 chủ đề.
- **Số người nói**: 8-15 người.
- **Độ dài mỗi file**: 1-5 phút (đủ nội dung, giảm thời gian STT).

## 2) Cấu trúc dữ liệu tối thiểu

Tạo file manifest CSV: `src/pilot_manifest.csv`

```csv
file_path,topic_id,speaker_id,split
Am_Thanh_Data/topic_a/speaker_01_001.mp3,topic_a,speaker_01,index
Am_Thanh_Data/topic_a/speaker_01_002.mp3,topic_a,speaker_01,query_seen
Am_Thanh_Data/topic_new/speaker_99_001.mp3,topic_new,speaker_99,query_unseen
```

Ý nghĩa cột:
- `split=index`: dùng để build kho dữ liệu tìm kiếm.
- `split=query_seen`: truy vấn có chủ đề đã tồn tại trong kho index.
- `split=query_unseen`: truy vấn có chủ đề mới chưa có trong kho index.

## 3) Quy trình chạy test nhanh

1. **Index pilot set**
   - Đặt file âm thanh pilot vào `Am_Thanh_Data`.
   - Chạy pipeline index: `python src/core/main.py`.
2. **Chạy truy vấn**
   - Chạy nhiều query trong `query_seen` và `query_unseen`.
   - Lệnh đơn file: `python src/core/retrieval.py <query_audio_path> 3`.
3. **Đánh giá tự động**
   - Dùng script đánh giá: `python src/core/evaluate_retrieval.py --manifest src/pilot_manifest.csv --top-k 3`.
4. **Lưu evidence cho báo cáo**
   - Giữ toàn bộ file `*_retrieval_results.json`.
   - Lưu summary CSV/JSON từ script evaluate.

## 4) Điều kiện pass pilot

- Hệ thống trả đủ 2 cột kết quả (top-3 content, top-3 voice) cho đa số query hợp lệ.
- `precision@3_content` và `precision@3_voice` vượt ngưỡng tự đặt (ví dụ >= 0.6 trong pilot).
- Latency truy vấn trung bình đáp ứng demo (ví dụ < 10s/query trên máy hiện tại).
- Không có lỗi vỡ pipeline khi gặp file query chủ đề mới (`query_unseen`).

## 5) Logic kiểm thử seen/unseen

- **Seen topic**: kỳ vọng top-k nội dung trả về nhiều file cùng `topic_id`.
- **Unseen topic**: không ép phải trùng chủ đề, nhưng hệ thống vẫn phải trả kết quả ổn định và có thể giải thích được qua transcript/keywords.
- **Voice retrieval**: kỳ vọng top-k giọng trả về cùng `speaker_id` nhiều nhất có thể.

## 6) Sau khi pilot đạt

1. Mở rộng crawler để đủ 500 file.
2. Giữ nguyên protocol đánh giá để so sánh trước/sau scale.
3. Chạy indexing theo lô lớn, sau đó chạy full evaluation và chốt số liệu cuối.
