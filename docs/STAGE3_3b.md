# Tài liệu 3b - Ghi chép lưu DB, truy vấn và log trung gian

**Mục lục & luồng chạy toàn đồ án:** `docs/README.md`.

## 1) Quá trình lưu CSDL lai

Script: `src/stage3/database_builder.py`

- Đọc dữ liệu đặc trưng từ `src/artifacts/stage2/stage2_features.jsonl`.
- (Mới) Có thể lọc theo manifest `dataset_index.csv` chỉ lấy `split_role=index` để tránh rò rỉ query vào kho tìm kiếm.
- Chuẩn hóa L2 toàn bộ vector nội dung (384d) và giọng nói (192d).
- Add vector vào:
  - `src/artifacts/stage3/content.index`
  - `src/artifacts/stage3/voice.index`
- Ghi metadata + mapping ID vào:
  - `src/artifacts/stage3/audio_hybrid.db` (bảng `audio_metadata`)

Output tổng hợp:
- `src/artifacts/stage3/database_build_summary.json`

## 2) Cách truy vấn top-3

Script: `src/stage3/retrieval_top3.py`

Ví dụ:

```bash
python src/stage3/retrieval_top3.py "src/Processed_Audio_Data/ĐỐI NHÂN XỬ THẾ/5_tips_ung_xu_giao_tiep_ban_nen_biet.wav" \
  --sqlite-db src/artifacts/stage3/audio_hybrid.db \
  --content-index src/artifacts/stage3/content.index \
  --voice-index src/artifacts/stage3/voice.index \
  --top-k 3 \
  --whisper-model tiny \
  --stt-max-duration-s 90 \
  --voice-max-duration-s 90 \
  --output-log src/artifacts/stage3/retrieval_query_log.json
```

## 3) Thuật toán đo tương tự (đã chuẩn hóa thuật ngữ)

- Nội dung:
  - Vector truy vấn: `q_c` (384d), vector kho: `x_c`.
  - Sau L2 normalize, dùng `sim_content = q_c . x_c` (inner product) == cosine similarity.
  - Sắp xếp giảm dần theo `sim_content`, lấy top-3.

- Giọng nói:
  - Vector truy vấn: `q_v` (192d), vector kho: `x_v`.
  - Sau L2 normalize, dùng `sim_voice = q_v . x_v` (inner product) == cosine similarity.
  - Sắp xếp giảm dần theo `sim_voice`, lấy top-3.

## 4) Log / kết quả trung gian phục vụ báo cáo

File log truy vấn: `src/artifacts/stage3/retrieval_query_log.json`

Bao gồm:
- `query_vectors_preview`: vài phần tử đầu của vector truy vấn nội dung/giọng.
- `distance_matrix_logs`:
  - `content_similarity_scores`
  - `content_cosine_distances = 1 - similarity`
  - `voice_similarity_scores`
  - `voice_cosine_distances = 1 - similarity`
- `content_top3`, `voice_top3` kèm tên file, đường dẫn, điểm tương đồng.

## 4.1) Chạy end-to-end theo split role cho YC3

Script: `src/stage3/run_requirement3_pipeline.py`

- Build DB/FAISS chỉ từ `split_role=index`.
- Tự động chạy query cho `query_seen` và `query_unseen`.
- Lưu log từng query + log tổng hợp để đưa vào báo cáo.

## 5) Tự phản biện phạm vi

- Bám sát đề:
  - Có kiến trúc CSDL lai metadata + vector index.
  - Có 2 nhánh top-3 độc lập (nội dung/giọng).
  - Có log trung gian để đưa vào báo cáo.
- Không lạc đề:
  - Không thêm mô hình ngoài phạm vi.
  - Không mở rộng sang kiến trúc phân tán hay service phức tạp.
