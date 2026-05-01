# Checklist sẵn sàng scale lên 500 file

**Luồng chạy chi tiết:** `docs/CLONE_AND_RUN.md`. **Mục lục tài liệu:** `docs/README.md`.

## 0. Phạm vi môn học (để tránh over-engineering)

- Chỉ giữ phần cốt lõi: chuẩn hóa audio, lập chỉ mục metadata, trích đặc trưng, tìm kiếm top-k, đánh giá cơ bản.
- Không bắt buộc các hạng mục enterprise như governance nhiều tầng, workflow gán nhãn nhiều người, versioning dữ liệu phức tạp.
- Mục tiêu chính: hoàn thành đúng yêu cầu đề và giải thích rõ thuật toán ở Giai đoạn 2-3.

## A. Nhất quán thuật ngữ

- [x] Mô tả nội dung thống nhất: Whisper + YAKE + SentenceTransformer.
- [x] Duy trì tương thích với schema cũ (`tfidf_keywords`) nhưng trình bày là "keywords".
- [x] Cập nhật mô tả trong code để tránh nhầm YAKE là TF-IDF.

## B. Cấu hình môi trường

- [x] Tách thông số DB ra biến môi trường (`DB_*`).
- [x] Tách thông số crawler ra biến môi trường (`FFMPEG_PATH`, output dir, archive file).
- [x] Cung cấp file mẫu `.env.example`.
- [x] Cung cấp `requirements.txt` để tái lập môi trường.

## C. Batch indexing

- [x] Thêm cấu hình `FAISS_SAVE_INTERVAL` (mặc định 20 file/lần save).
- [x] Save FAISS theo lô + save nốt ở cuối run.
- [x] Giữ cơ chế skip file đã tồn tại để tránh index trùng.

## D. Checklist chạy production 500 file (luồng Stage 3 — khuyến nghị)

1. Môi trường + `pip install -r requirements.txt`, FFmpeg (`PATH` hoặc `FFMPEG_PATH`).
2. `python src/stage1/crawl_audio.py` (hoặc đặt WAV đúng cấu trúc + rebuild CSV).
3. `python src/stage2/batch_feature_extraction.py --input-dir src/Processed_Audio_Data --output-jsonl src/artifacts/stage2/stage2_features.jsonl ...`
4. `python src/stage3/run_requirement3_pipeline.py` (build DB chỉ `split_role=index` + chạy query seen/unseen).
5. Kiểm `database_build_summary.json` (`inserted_records` / vector = kỳ vọng).
6. Demo: `python src/stage4/demo_cli.py "<wav>"`.
7. Lưu copy log JSON cho báo cáo.

## D2. Checklist thay thế (nhánh `src/core/` + MySQL)

1. Biến môi trường `.env` cho DB.
2. Chạy index batch: `python src/core/main.py`.
3. Truy vấn mẫu: `python src/core/retrieval.py <query_file> 3`.
4. Đánh giá: `python src/core/evaluate_retrieval.py --manifest <manifest.csv> --top-k 3`.
5. Lưu summary + log trung gian.

**Ghi chú:** Mục **C. Batch indexing** (save FAISS theo lô) áp dụng chủ yếu cho **`src/core/main.py`**. Luồng Stage 3 build FAISS một lần trong `database_builder.py`.