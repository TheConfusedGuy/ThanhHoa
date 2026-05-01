# Bộ metric và log trung gian cho báo cáo

**Mục lục docs:** `docs/README.md`.

## 0) Hai nguồn log/metric

| Nguồn | Khi nào | File / script |
|--------|---------|----------------|
| **Stage 3 (SQLite + FAISS)** | Luồng đồ án `run_requirement3_pipeline.py` / `retrieval_top3.py` | `src/artifacts/stage3/requirement3_query_logs.json`, `query_logs/query_*.json` — chứa `query_vector_shapes`, `distance_matrix_logs` (D/I), `content_top3`, `voice_top3` |
| **Core MySQL + evaluate** | Đánh giá formal precision@k | `src/core/evaluate_retrieval.py`, output trong `artifacts/eval_outputs/` (theo manifest pilot) |

---

## 1) Metric bắt buộc (nhánh Core / manifest)

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

### Luồng Stage 3 (khuyến nghị)

1. Trích một query mẫu từ `requirement3_query_logs.json`: ma trận `content_D_matrix` / `voice_D_matrix`, top-3 hai nhánh.
2. Ảnh chụp CLI **`python src/stage4/demo_cli.py`** (hai cột top-3).

### Luồng Core + evaluate

1. Trích bảng tổng hợp từ `retrieval_eval_summary.json`.
2. Chọn 2-3 dòng tiêu biểu từ `retrieval_eval_details.jsonl`:
   - 1 query thuộc `query_seen` có kết quả tốt.
   - 1 query thuộc `query_unseen` để chứng minh hệ thống vẫn trả về top-k ổn định.
3. Đính kèm ảnh chụp màn hình CLI `src/core/retrieval.py` (nếu dùng nhánh MySQL).
