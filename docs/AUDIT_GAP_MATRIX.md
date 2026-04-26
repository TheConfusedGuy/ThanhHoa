# Ma trận đối chiếu Đề bài - Kế hoạch - Hiện trạng

Tài liệu này chốt nhanh trạng thái "đã đạt/chưa đạt" để bám sát rubric trước khi scale lên 500 file.

## 1) Yêu cầu đề bài

| Mục đề bài | Ý nghĩa rubric | Hiện trạng dự án | Đánh giá |
|---|---|---|---|
| 1. Bộ dữ liệu âm thanh chủ đề rõ ràng, 1 người nói/file | Có dữ liệu, có cấu trúc metadata, có chuẩn hóa cơ bản | Có script crawl + metadata + archive tải; chưa đóng gói tiêu chuẩn dữ liệu thành tài liệu chuẩn | Đạt một phần |
| 2. Thuộc tính nhận diện nội dung và giọng nói + giải thích lý do | Có đặc trưng nội dung và giọng nói, giải thích nguyên lý trích xuất | Có Whisper + YAKE + sentence embedding; có MFCC + ECAPA; giải thích nằm rải rác trong code, chưa có tài liệu báo cáo chính thức | Đạt kỹ thuật, thiếu hồ sơ |
| 3. Tìm kiếm đầu vào mới, trả top-3 nội dung và top-3 giọng | Có pipeline truy vấn chạy được, xếp theo similarity giảm dần | `retrieval.py` đã trả 2 nhánh top-k (mặc định 3), có in kết quả và lưu JSON | Đạt |
| 3a. Sơ đồ khối + quy trình | Có thể mô tả được kiến trúc và luồng xử lý | Chưa có file sơ đồ chính thức cho báo cáo | Chưa đạt hồ sơ |
| 3b. Trình bày trích rút, lưu CSDL, kết quả trung gian | Cần mô tả rõ cách lưu, truy vấn, và log trung gian | Có MySQL + FAISS + JSON output; chưa có tài liệu tổng hợp chuẩn rubric | Đạt kỹ thuật, thiếu hồ sơ |
| 4. Demo và đánh giá kết quả | Cần demo chạy thật + chỉ số định lượng | Có CLI demo; chưa có script metric tổng hợp | Đạt một phần |

## 2) Đối chiếu theo kế hoạch 4 giai đoạn

| Giai đoạn | Kế hoạch | Hiện trạng | Mức độ |
|---|---|---|---|
| GĐ1 - Dữ liệu | Chuẩn tiêu chuẩn, thu thập, kiểm duyệt, tiền xử lý | Có crawl + metadata; chưa có checklist kiểm duyệt thống nhất và tài liệu chuẩn dữ liệu | Trung bình |
| GĐ2 - Đặc trưng & báo cáo | Chọn thuộc tính, giải thích nguyên lý, script tự động | Script lõi đã có; thiếu tài liệu report độc lập | Tốt về kỹ thuật |
| GĐ3 - CSDL & tìm kiếm | Thiết kế DB, lưu vector, top-3 content/voice, kết quả trung gian | Hoàn chỉnh ở mức chạy hệ thống; cần tối ưu batch và nhất quán thuật ngữ | Tốt |
| GĐ4 - Demo & đánh giá | Test seen/unseen, UI/CLI, kết luận | Có CLI; chưa có bộ đánh giá định lượng chuẩn | Trung bình |

## 3) Các gap quan trọng cần xử lý trước khi scale 500 file

1. Chốt bộ test nhanh (30-80 file) có nhãn nhẹ (topic_id, speaker_id) để đo precision@3.
2. Chuẩn hóa thuật ngữ nội dung (tránh nhầm TF-IDF và YAKE trong phần trình bày).
3. Tách cấu hình nhạy cảm ra biến môi trường (`DB_PASSWORD`, `FFMPEG_PATH`, ...).
4. Giảm ghi đĩa FAISS theo từng file bằng cơ chế commit theo lô.
5. Thêm script đánh giá để xuất kết quả trung gian và chỉ số định lượng phục vụ demo/báo cáo.

## 4) Kết luận phản biện

- Tư duy kiến trúc của kế hoạch là đúng và có logic triển khai.
- Dự án hiện tại mạnh ở phần "kỹ thuật lõi", yếu ở phần "hồ sơ chứng minh" và "đánh giá định lượng".
- Chiến lược test nhanh trước, scale 500 sau là lựa chọn đúng để giảm chi phí thử-sai.
