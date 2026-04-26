# Bộ metric và log trung gian cho báo cáo

Tài liệu này chuẩn hóa phần đánh giá để đáp ứng yêu cầu demo + kết quả trung gian.

## 1) Metric bắt buộc

- `precision@3_content`: tỷ lệ kết quả trong top-3 có cùng `topic_id` với query.
- `precision@3_voice`: tỷ lệ kết quả trong top-3 có cùng `speaker_id` với query.
- `latency_s`: thời gian phản hồi của truy vấn (giây).

Các metric này được tính tự động bởi `src/core/evaluate_retrieval.py`.

## 2) Log trung gian cần lưu

### 2.1 Per-query detail log (JSONL)

File: `src/artifacts/eval_outputs/retrieval_eval_details.jsonl`

Mỗi dòng là 1 truy vấn, gồm:
- thông tin query: `query_filename`, `query_split`, `expected_topic_id`, `expected_speaker_id`
- kết quả retrieval: `content_matches`, `voice_matches`
- metric per-query: `precision_at_k_content`, `precision_at_k_voice`, `latency_s`

### 2.2 Tổng hợp summary (JSON)

File: `src/artifacts/eval_outputs/retrieval_eval_summary.json`

Gồm:
- số lượng query đã đánh giá
- precision@k trung bình cho content/voice
- latency trung bình và trung vị
- tách theo split `query_seen` / `query_unseen`

## 3) Lệnh chạy chuẩn

```bash
python src/core/evaluate_retrieval.py --manifest src/pilot_manifest.csv --top-k 3
```

## 4) Cách đưa vào báo cáo

1. Trích bảng tổng hợp từ `retrieval_eval_summary.json`.
2. Chọn 2-3 dòng tiêu biểu từ `retrieval_eval_details.jsonl`:
   - 1 query thuộc `query_seen` có kết quả tốt.
   - 1 query thuộc `query_unseen` để chứng minh hệ thống vẫn trả về top-k ổn định.
3. Đính kèm ảnh chụp màn hình CLI `src/core/retrieval.py` để chứng minh demo chạy thật.
