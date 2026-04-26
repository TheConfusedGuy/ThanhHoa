# Tài liệu 2.2 - Nguyên lý trích rút các đặc trưng

## 1. Tổng quan luồng trích rút

Đầu vào là tín hiệu âm thanh đơn kênh 16kHz. Hệ thống trích rút hai nhánh:
- **Nhánh nội dung**: âm thanh -> văn bản -> embedding ngữ nghĩa.
- **Nhánh giọng nói**: âm thanh -> đặc trưng âm học + speaker embedding.

## 2. Nguyên lý trích rút đặc trưng nội dung

### 2.1 ASR bằng Whisper

Whisper là mô hình encoder-decoder huấn luyện đa ngôn ngữ cho bài toán nhận dạng tiếng nói tự động.

Quy trình mức cao:
1. Chuyển sóng âm thành biểu diễn phổ thời gian-tần số.
2. Encoder học biểu diễn ngữ âm-ngữ cảnh.
3. Decoder sinh chuỗi token văn bản theo xác suất hậu nghiệm.

Kết quả là transcript phục vụ các bước xử lý ngôn ngữ tiếp theo.

### 2.2 Trích từ khóa bằng YAKE + ViTokenizer

`ViTokenizer` chuẩn hóa/tách từ tiếng Việt giúp giảm sai lệch ranh giới từ.

`YAKE` đánh giá độ quan trọng từ/cụm từ theo các tín hiệu cục bộ (vị trí, tần suất, phân bố...) mà không cần huấn luyện corpus riêng.

Trong cài đặt hiện tại, điểm YAKE được chuẩn hóa về miền [0,1] để thuận tiện lưu trữ và hiển thị.

### 2.3 Nhúng ngữ nghĩa bằng SentenceTransformer

SentenceTransformer ánh xạ câu/đoạn văn thành vector dày đặc cố định số chiều (384-d).

Tư tưởng cốt lõi:
- Các câu gần nghĩa sẽ nằm gần nhau trong không gian vector.
- Độ tương đồng có thể tính nhanh bằng cosine similarity (sau L2-normalization).

Nhờ đó, hệ thống tìm kiếm nội dung theo nghĩa thay vì chỉ theo khớp từ bề mặt.

## 3. Nguyên lý trích rút đặc trưng giọng nói

### 3.1 MFCC

MFCC được tính theo chuỗi bước:
1. Chia tín hiệu thành các khung ngắn theo thời gian.
2. Biến đổi Fourier (FFT) để về miền tần số.
3. Áp dụng bank lọc theo thang Mel (gần với cảm nhận tai người).
4. Lấy log năng lượng.
5. Biến đổi Cosine rời rạc (DCT) để thu các hệ số cepstral.

Trong hệ thống, lấy **mean/std theo thời gian** để có vector nhỏ gọn và ổn định.

### 3.2 Pitch, Energy, ZCR

- **Pitch**: tần số cơ bản (F0), phản ánh cao độ.
- **Energy (RMS)**: cường độ tín hiệu theo thời gian.
- **ZCR**: số lần đổi dấu của tín hiệu trên mỗi khung, phản ánh mức dao động nhanh/chậm.

Các thống kê mean/std của các đại lượng này bổ sung thông tin vật lý cho nhận diện giọng.

### 3.3 Speaker Embedding bằng ECAPA-TDNN

ECAPA-TDNN là mạng nơ-ron sâu cho bài toán speaker recognition:
- TDNN học ngữ cảnh theo trục thời gian.
- Cơ chế channel attention và aggregation giúp tăng độ phân biệt danh tính.

Đầu ra embedding 192 chiều được dùng như chữ ký giọng nói của người nói.

## 4. Chuẩn hóa vector cho truy vấn tương đồng

Cả semantic embedding và speaker embedding được chuẩn hóa L2:

\\[
\hat{v} = \\frac{v}{\\|v\\|_2}
\\]

Sau chuẩn hóa, tích vô hướng tương đương cosine similarity, phù hợp cho truy vấn top-k trong không gian vector.

## 5. Kết luận

Pipeline hiện tại đáp ứng mục tiêu của yêu cầu 2:
- Có đặc trưng nội dung và đặc trưng giọng nói.
- Có cơ sở toán học và nguyên lý trích rút rõ ràng.
- Đầu ra ở dạng vector nhỏ gọn, thuận tiện cho lưu trữ và truy vấn tương đồng.
