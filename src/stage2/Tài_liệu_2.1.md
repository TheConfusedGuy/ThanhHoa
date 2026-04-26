# Tài liệu 2.1 - Lý do lựa chọn và giá trị thông tin của các thuộc tính

## 1. Mục tiêu của Giai đoạn 2

Mục tiêu của giai đoạn này là xây dựng bộ thuộc tính đặc trưng nhỏ gọn, có khả năng biểu diễn:
- **Nội dung ngữ nghĩa** của file âm thanh.
- **Đặc tính giọng nói cá nhân** của người nói.

Các thuộc tính được thiết kế theo nguyên tắc MMDBMS: biểu diễn dữ liệu đa phương tiện thành vector đa chiều để phục vụ lưu trữ và truy vấn tương đồng nhanh trong không gian vector.

## 2. Nhóm thuộc tính nhận diện nội dung

### 2.1 Whisper ASR (Speech-to-Text)

- File âm thanh được chuyển thành văn bản bằng mô hình Whisper.
- Việc chuyển từ tín hiệu âm thanh sang văn bản giúp hệ thống khai thác lớp thông tin ngôn ngữ bậc cao (ngữ nghĩa).

**Giá trị thông tin:** tạo cầu nối giữa dữ liệu âm thanh và các phương pháp biểu diễn ngôn ngữ hiện đại.

### 2.2 YAKE + ViTokenizer (Keyword extraction)

- `ViTokenizer` tách từ tiếng Việt theo đơn vị từ đúng ngữ pháp.
- `YAKE` trích xuất các từ khóa quan trọng theo hướng unsupervised.

**Giá trị thông tin:** tạo tập thuộc tính trọng yếu (keywords) để mô tả nhanh chủ đề.

### 2.3 SentenceTransformer (BERT-family semantic embedding)

- Văn bản phiên âm được ánh xạ thành vector ngữ nghĩa 384 chiều bằng mô hình `paraphrase-multilingual-MiniLM-L12-v2`.
- Vector embedding cho phép so sánh nội dung bằng khoảng cách vector thay vì so khớp chuỗi ký tự.

**Giá trị thông tin:** nắm bắt ngữ cảnh và mức độ tương đồng ý nghĩa tốt hơn cách đếm từ.

## 3. Vì sao không dùng TF-IDF/Word2Vec trong phạm vi này

- **TF-IDF** thường tạo vector thưa, số chiều lớn và phụ thuộc mạnh vào từ vựng cục bộ của tập dữ liệu.
- **Word2Vec** biểu diễn mức từ, cần thêm bước tổng hợp để thành biểu diễn câu/đoạn.

Trong phạm vi đồ án này, `SentenceTransformer` cho biểu diễn câu trực tiếp, gọn hơn cho truy vấn tương đồng ngữ nghĩa.

## 4. Nhóm thuộc tính nhận diện giọng nói

### 4.1 Đặc trưng âm học mức thấp (librosa)

- **MFCC (mean/std):** mô tả phổ âm theo thang Mel, mô phỏng cảm nhận thính giác người.
- **Pitch (mean/std):** phản ánh cao độ cơ bản.
- **Energy RMS (mean/std):** phản ánh cường độ phát âm.
- **ZCR (mean/std):** phản ánh mức biến thiên dấu tín hiệu, hỗ trợ phân biệt kiểu âm thanh.

**Giá trị thông tin:** tạo lớp đặc trưng vật lý nhỏ gọn, tính toán nhanh, hỗ trợ tốt cho lọc và phân tích giọng nói.

### 4.2 Speaker Embedding bằng ECAPA-TDNN (speechbrain)

- Mô hình ECAPA-TDNN sinh embedding 192 chiều đại diện danh tính giọng nói.
- Embedding này tập trung vào đặc tính người nói, ít phụ thuộc nội dung câu nói.

**Giá trị thông tin:** tăng khả năng nhận diện người nói ổn định khi nội dung phát biểu thay đổi.

## 5. Vì sao không dùng Mel-spectrogram/x-vector trong phạm vi này

- Mel-spectrogram là biểu diễn trung gian hữu ích nhưng nếu đã có MFCC và embedding ECAPA thì bổ sung thêm sẽ làm tăng dư thừa dữ liệu.
- x-vector không được chọn trong bản triển khai này vì ECAPA-TDNN đã đáp ứng tốt vai trò speaker embedding với pipeline hiện tại.

## 6. Kết luận

Bộ thuộc tính được chọn gồm:
- **Nội dung:** `transcript`, `keywords`, `semantic embedding`.
- **Giọng nói:** `MFCC`, `pitch`, `energy`, `ZCR`, `speaker embedding`.

Đây là cấu hình cân bằng giữa độ giàu thông tin và chi phí tính toán, phù hợp mục tiêu retrieval trên cơ sở dữ liệu âm thanh trong đồ án.
