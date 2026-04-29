# Tài liệu 3a - Quy trình thực hiện Giai đoạn 3 theo sơ đồ khối

## Mục tiêu

Xây dựng hệ thống tìm kiếm file âm thanh với kiến trúc CSDL lai:
- SQLite (hoặc MySQL nếu cần triển khai server) để lưu metadata và ánh xạ `file_id`.
- FAISS để lưu và truy vấn vector đặc trưng nội dung/giọng nói.

Đầu vào là file âm thanh mới. Đầu ra gồm 2 danh sách top-3:
- Top-3 giống nhất về nội dung.
- Top-3 giống nhất về giọng nói.

## Sơ đồ khối luồng đi

```mermaid
flowchart LR
  A[Khối Đầu vào\nFile âm thanh mới] --> B[Khối Xử lý truy vấn\nWhisper + SentenceTransformer\nECAPA-TDNN]
  B --> C1[Vector nội dung 384d\nL2 normalize]
  B --> C2[Vector giọng nói 192d\nL2 normalize]
  C1 --> D1[FAISS content.index\nIndexFlatIP]
  C2 --> D2[FAISS voice.index\nIndexFlatIP]
  D1 --> E[Khối CSDL Metadata\nSQLite audio_metadata]
  D2 --> E
  E --> F[Khối Kết quả\nTop-3 content\nTop-3 voice]
```

## Quy trình thực hiện chi tiết

1. Chuẩn bị đầu vào từ Giai đoạn 2:
   - File `stage2_features.jsonl` chứa transcript, keywords, content embedding, speaker embedding.

2. Khởi tạo CSDL metadata:
   - Tạo bảng `audio_metadata` gồm: `file_id`, `file_name`, `file_path`,
     `transcript_text`, `keywords`, `duration`, `content_faiss_id`, `voice_faiss_id`.

3. Khởi tạo hai FAISS index độc lập:
   - `content.index`: `IndexFlatIP`, dim = 384.
   - `voice.index`: `IndexFlatIP`, dim = 192.

4. Chuẩn hóa vector L2 trước khi add vào FAISS:
   - Với mọi vector `v`, dùng `v_hat = v / ||v||_2`.
   - Khi dùng `IndexFlatIP`, điểm inner product trên vector đã chuẩn hóa sẽ tương đương cosine similarity.

5. Đổ dữ liệu và ánh xạ ID:
   - Add vector nội dung và giọng nói vào 2 index.
   - Lấy `content_faiss_id`, `voice_faiss_id` theo thứ tự add.
   - Ghi metadata + 2 FAISS ID vào bảng `audio_metadata`.

6. Truy vấn top-3:
   - Trích xuất vector truy vấn từ file âm thanh mới.
   - L2 normalize vector truy vấn.
   - Search top-k trên 2 index FAISS.
   - Map `faiss_id` về metadata qua bảng SQLite.
   - Trả kết quả theo thứ tự similarity giảm dần.

## Lệnh chạy chính

```bash
python src/stage3/database_builder.py \
  --stage2-jsonl src/artifacts/stage2/stage2_features.jsonl \
  --sqlite-db src/artifacts/stage3/audio_hybrid.db \
  --content-index src/artifacts/stage3/content.index \
  --voice-index src/artifacts/stage3/voice.index
```
