# Giai đoạn 2 - Trạng thái hoàn thiện theo yêu cầu 2

## 1) Thành phần code đã gom vào một folder

Toàn bộ code liên quan yêu cầu 2 đã đặt trong `src/stage2/`:

- `content_feature_extractor.py`
- `voice_feature_extractor.py`
- `batch_feature_extraction.py`
- `demo_content_extractor.py`
- `Tài_liệu_2.1.md`
- `Tài_liệu_2.2.md`

`src/core/main.py` và `src/core/retrieval.py` đã cập nhật import sang `stage2.*`.

## 2) Đối chiếu yêu cầu 2 với code hiện tại

### Nội dung (Speech Retrieval)

- Whisper ASR: **Đã có**
- YAKE + ViTokenizer: **Đã có**
- SentenceTransformer (BERT-family): **Đã có**
- TF-IDF: **Không dùng**
- Word2Vec: **Không dùng**

### Giọng nói (Speaker Identification)

- MFCC (mean/std): **Đã có**
- Pitch, Energy, ZCR: **Đã có**
- ECAPA-TDNN speaker embedding: **Đã có**
- Mel-spectrogram: **Không dùng**
- x-vector: **Không dùng**

## 3) Tài liệu học thuật

- `src/stage2/Tài_liệu_2.1.md`: Lý do lựa chọn + giá trị thông tin thuộc tính.
- `src/stage2/Tài_liệu_2.2.md`: Nguyên lý toán học/hoạt động trích rút đặc trưng.

Nội dung tài liệu khớp trực tiếp với công nghệ đã triển khai trong code.
