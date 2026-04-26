# Checklist sẵn sàng scale lên 500 file

Tài liệu này dùng như gate trước khi chạy batch cuối.

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

## D. Checklist chạy production 500 file

1. Tạo môi trường và cài dependencies.
2. Điền biến môi trường trong `.env`.
3. Crawl dữ liệu đủ 500 file, chuẩn hóa thư mục dữ liệu.
4. Chạy index batch: `python src/core/main.py`.
5. Chạy truy vấn mẫu: `python src/core/retrieval.py <query_file> 3`.
6. Chạy đánh giá pilot/final: `python src/core/evaluate_retrieval.py --manifest <manifest.csv> --top-k 3`.
7. Lưu summary + log trung gian cho báo cáo.
