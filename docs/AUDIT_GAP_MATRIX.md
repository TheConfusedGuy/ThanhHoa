# Ma trận đối chiếu Đề bài — Hiện trạng — Tài liệu chứng minh

Tài liệu cập nhật để phản ánh **luồng báo cáo khuyến nghị**: Stage 1→4 (`stage1`…`stage4`) với **SQLite + FAISS**, đồng thời ghi nhận nhánh **`src/core/`** (MySQL + đánh giá formal).

**Mục lục chi tiết + lệnh chạy + output:** `docs/README.md`.

---

## 1) Yêu cầu đề bài

| Mục đề bài | Ý nghĩa rubric | Hiện trạng & chứng cứ | Đánh giá |
|------------|----------------|------------------------|----------|
| **1.** Bộ dữ liệu ≥500*, chủ đề rõ, 1 speaker/file (theo thiết kế), chuẩn hóa | Dữ liệu + metadata + WAV chuẩn | `crawl_audio.py`, `Processed_Audio_Data/`, `artifacts/stage1/dataset_index.csv`; kiểm vector/index: `database_build_summary.json` | **Đạt** khi đã crawl/build đủ (môi trường cục bộ) |
| **2.** Thuộc tính nội dung + giọng + **lý do & nguyên lý** | Đặc trưng đúng danh mục + báo cáo | Code `stage2/`; **`src/stage2/Tài_liệu_2.1.md`**, **`Tài_liệu_2.2.md`**; `STAGE2_STATUS.md` | **Đạt** |
| **3.** Tìm kiếm file mới → top-3 nội dung + top-3 giọng (similarity giảm dần) | Hai nhánh retrieval | `retrieval_top3.py`, `run_requirement3_pipeline.py`; log JSON | **Đạt** |
| **3a.** Sơ đồ khối + quy trình | Hồ sơ báo cáo | **`docs/STAGE3_3a.md`** (Mermaid + thuật toán Top-3) | **Đạt** |
| **3b.** Trích rút, lưu CSDL, kết quả trung gian | Mô tả + log | **`docs/STAGE3_3b.md`**; `distance_matrix_logs` trong JSON query | **Đạt** |
| **4.** Demo & đánh giá | Chạy thật + nhận xét seen/unseen | `stage4/demo_cli.py`; `requirement3_query_logs.json`; metric formal có thể thêm qua `core/evaluate_retrieval.py` | **Đạt** (CLI); GUI upload là **tùy chọn** |

\*500: không kiểm trong Git (âm thanh/artifact thường `.gitignore`); chứng minh trên máy chạy pipeline.

---

## 2) Đối chiếu bốn giai đoạn kế hoạch

| Giai đoạn | Kế hoạch | Hiện trạng | Tài liệu |
|-----------|-----------|------------|----------|
| **GĐ1** | Chuẩn, thu thập, QC, tiền xử lý, chỉ mục | Crawler + FFmpeg + CSV manifest | `STAGE1_STATUS.md`, `CLONE_AND_RUN.md` |
| **GĐ2** | Thuộc tính + lý thuyết + batch | Batch JSONL + tài liệu 2.1/2.2 | `STAGE2_STATUS.md`, `Tài_liệu_2.*` |
| **GĐ3** | DB + vector + top-3 + log | SQLite + FAISS `IndexFlatIP` + L2 | `STAGE3_3a.md`, `STAGE3_3b.md` |
| **GĐ4** | Demo seen/unseen + đánh giá | Pipeline query + CLI demo | `CLONE_AND_RUN.md`, `METRICS_LOGGING_GUIDE.md` |

---

## 3) Gợi ý cải tiến (không chặn nộp đồ án)

1. **Thống nhất một luồng trong báo cáo:** Stage 3 SQLite hoặc Core MySQL — tránh trình bày lẫn hai kiến trúc như một.  
2. **Audit YC1:** mở rộng `audit_requirements_1_2.py` cho schema **`crawl_audio`** hoặc export CSV thứ hai cho audit.  
3. **`precision@k` formal:** chạy `evaluate_retrieval.py` với manifest tương thích nhánh Core — hoặc bổ script đánh giá cho đường Stage 3.

---

## 4) Kết luận

- **Hồ sơ:** đã có đủ mục 3a/3b và tài liệu Stage 2 trong repo.  
- **Chạy được:** luồng `run_requirement3_pipeline.py` + `demo_cli.py`.  
- **Người clone:** đọc `CLONE_AND_RUN.md` để tái tạo artifact.
