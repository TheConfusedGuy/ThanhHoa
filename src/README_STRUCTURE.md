# Cau truc thu muc `src`

Muc tieu: tach ro code, du lieu, va artifact de khong bi roi.

## Code chinh

- `core/main.py`: pipeline index vao FAISS + MySQL
- `core/retrieval.py`: truy van top-k content/voice
- `core/db_manager.py`, `core/faiss_manager.py`: lop ha tang luu tru/tim kiem
- `core/evaluate_retrieval.py`: danh gia retrieval

## Theo giai doan

- `stage1/`: chuan bi du lieu (crawl, preprocess, index metadata)
- `stage2/`: trich xuat dac trung noi dung + giong noi, tai lieu 2.1/2.2
- `stage3/`: build CSDL lai SQLite + FAISS, truy van top-3 content/voice

## Tai lieu

- `../docs/`: toan bo tai lieu bao cao va checklist
  - bo sung `STAGE3_3a.md`, `STAGE3_3b.md` cho Giai doan 3

## Du lieu

- `Am_Thanh_Data/`: du lieu am thanh dau vao
- `Processed_Audio_Data/`: du lieu sau chuan hoa

## Artifact sinh ra khi chay

- `artifacts/stage1/`: metadata, download archive, dataset index/summary cua Stage 1
- `artifacts/faiss/`: file index FAISS
- `artifacts/eval_outputs/`: ket qua danh gia retrieval

Luu y: cac file tam debug da duoc loai bo de giu workspace gon gang.
