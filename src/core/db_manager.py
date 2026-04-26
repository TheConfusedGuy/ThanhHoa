# -*- coding: utf-8 -*-
"""
db_manager.py
-------------
Quản lý kết nối MySQL và schema cho hệ thống lưu trữ dữ liệu âm thanh.

Bảng duy nhất: audio_records
  - Lưu Transcript, Keywords, Metadata (filename, duration...)
  - Lưu faiss_row_id để liên kết với vector tương ứng trong FAISS index
"""

import json
import os
import mysql.connector
from mysql.connector import Error


# ── Cấu hình kết nối MySQL ────────────────────────────────────────────────────
# Có thể override bằng biến môi trường:
#   DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_CHARSET
DB_CONFIG = {
    'host':     os.getenv('DB_HOST', 'localhost'),
    'port':     int(os.getenv('DB_PORT', '3306')),
    'user':     os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'CSDLDPT_audio_db'),
    'charset':  os.getenv('DB_CHARSET', 'utf8mb4'),
}

# ── SQL tạo database & bảng ───────────────────────────────────────────────────
_SQL_CREATE_DATABASE = (
    f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` "
    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
)

_SQL_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS `audio_records` (
    -- Khóa chính tự tăng
    `id`                INT          NOT NULL AUTO_INCREMENT,
    PRIMARY KEY (`id`),

    -- Định danh file
    `file_id`           VARCHAR(255) NOT NULL UNIQUE COMMENT 'ID tạo từ tên file',
    `filename`          VARCHAR(500) NOT NULL        COMMENT 'Tên file gốc',
    `file_path`         TEXT         NOT NULL        COMMENT 'Đường dẫn đầy đủ',

    -- Metadata kỹ thuật
    `duration_seconds`  FLOAT        DEFAULT 0       COMMENT 'Thời lượng (giây)',
    `file_size_bytes`   BIGINT       DEFAULT 0       COMMENT 'Kích thước file (bytes)',

    -- Nội dung ngữ nghĩa
    `transcript`        LONGTEXT                     COMMENT 'Phiên âm từ Whisper',
    `tfidf_keywords`    JSON                         COMMENT 'Top-10 từ khóa quan trọng {word: score}',

    -- Đặc trưng âm học (lưu dạng JSON array)
    `mfccs_mean`        JSON                         COMMENT 'Trung bình 13 hệ số MFCC',
    `mfccs_std`         JSON                         COMMENT 'Độ lệch chuẩn 13 hệ số MFCC',
    `pitch_mean`        FLOAT        DEFAULT 0       COMMENT 'Tần số cơ bản trung bình',
    `pitch_std`         FLOAT        DEFAULT 0       COMMENT 'Độ lệch chuẩn pitch',
    `energy_mean`       FLOAT        DEFAULT 0       COMMENT 'Năng lượng RMS trung bình',
    `energy_std`        FLOAT        DEFAULT 0       COMMENT 'Độ lệch chuẩn năng lượng',
    `zcr_mean`          FLOAT        DEFAULT 0       COMMENT 'Zero Crossing Rate trung bình',
    `zcr_std`           FLOAT        DEFAULT 0       COMMENT 'Độ lệch chuẩn ZCR',

    -- Liên kết FAISS (row index trong mỗi index)
    `content_faiss_id`  INT          DEFAULT -1      COMMENT 'Row ID trong faiss_content.index',
    `voice_faiss_id`    INT          DEFAULT -1      COMMENT 'Row ID trong faiss_voice.index',

    `created_at`        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX `idx_file_id`  (`file_id`),
    INDEX `idx_created`  (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


class DatabaseManager:
    """
    Quản lý kết nối MySQL và các thao tác CRUD cho bảng audio_records.
    """

    def __init__(self):
        self.connection = None
        self._connect_and_init()

    def _connect_and_init(self):
        """Kết nối MySQL, tạo database và bảng nếu chưa tồn tại."""
        try:
            print(f"[DB] Đang kết nối MySQL tại {DB_CONFIG['host']}:{DB_CONFIG['port']} ...")
            init_conn = mysql.connector.connect(
                host=DB_CONFIG['host'],
                port=DB_CONFIG['port'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                charset=DB_CONFIG['charset'],
            )
            cursor = init_conn.cursor()
            cursor.execute(_SQL_CREATE_DATABASE)
            cursor.close()
            init_conn.close()

            self.connection = mysql.connector.connect(**DB_CONFIG)
            cursor = self.connection.cursor()
            cursor.execute(_SQL_CREATE_TABLE)
            self.connection.commit()
            cursor.close()
            print('[DB] Kết nối MySQL thành công. Bảng audio_records đã sẵn sàng.')

        except Error as e:
            print(f'[DB][ERROR] Không thể kết nối MySQL: {e}')
            self.connection = None

    def _ensure_connection(self):
        if self.connection is None:
            self._connect_and_init()
        elif not self.connection.is_connected():
            print('[DB] Kết nối bị mất, đang kết nối lại...')
            self.connection.reconnect(attempts=3, delay=2)

    def insert_record(self, data: dict) -> int:
        self._ensure_connection()
        if self.connection is None:
            return -1

        sql = """
            INSERT INTO audio_records (
                file_id, filename, file_path,
                duration_seconds, file_size_bytes,
                transcript, tfidf_keywords,
                mfccs_mean, mfccs_std,
                pitch_mean, pitch_std,
                energy_mean, energy_std,
                zcr_mean, zcr_std,
                content_faiss_id, voice_faiss_id
            ) VALUES (
                %(file_id)s, %(filename)s, %(file_path)s,
                %(duration_seconds)s, %(file_size_bytes)s,
                %(transcript)s, %(tfidf_keywords)s,
                %(mfccs_mean)s, %(mfccs_std)s,
                %(pitch_mean)s, %(pitch_std)s,
                %(energy_mean)s, %(energy_std)s,
                %(zcr_mean)s, %(zcr_std)s,
                %(content_faiss_id)s, %(voice_faiss_id)s
            )
        """

        params = {
            'file_id':           data.get('file_id', ''),
            'filename':          data.get('filename', ''),
            'file_path':         data.get('file_path', ''),
            'duration_seconds':  data.get('duration_seconds', 0.0),
            'file_size_bytes':   data.get('file_size_bytes', 0),
            'transcript':        data.get('transcript', ''),
            'tfidf_keywords':    json.dumps(data.get('tfidf_keywords', {}), ensure_ascii=False),
            'mfccs_mean':        json.dumps(data.get('mfccs_mean', []), ensure_ascii=False),
            'mfccs_std':         json.dumps(data.get('mfccs_std', []), ensure_ascii=False),
            'pitch_mean':        data.get('pitch_mean', 0.0),
            'pitch_std':         data.get('pitch_std', 0.0),
            'energy_mean':       data.get('energy_mean', 0.0),
            'energy_std':        data.get('energy_std', 0.0),
            'zcr_mean':          data.get('zcr_mean', 0.0),
            'zcr_std':           data.get('zcr_std', 0.0),
            'content_faiss_id':  data.get('content_faiss_id', -1),
            'voice_faiss_id':    data.get('voice_faiss_id', -1),
        }

        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, params)
            self.connection.commit()
            record_id = cursor.lastrowid
            cursor.close()
            print(f"[DB] Đã lưu '{params['filename']}' → MySQL id={record_id}")
            return record_id
        except Error as e:
            print(f"[DB][ERROR] insert_record thất bại: {e}")
            try:
                self.connection.rollback()
            except Exception:
                pass
            return -1

    def record_exists(self, file_id: str) -> bool:
        self._ensure_connection()
        if self.connection is None:
            return False
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT 1 FROM audio_records WHERE file_id = %s LIMIT 1', (file_id,))
            result = cursor.fetchone()
            cursor.close()
            return result is not None
        except Error as e:
            print(f'[DB][ERROR] record_exists thất bại: {e}')
            return False

    def get_record_by_faiss_ids(self, content_faiss_ids: list) -> list:
        self._ensure_connection()
        if not content_faiss_ids or self.connection is None:
            return []
        placeholders = ', '.join(['%s'] * len(content_faiss_ids))
        sql = f"""
            SELECT id, file_id, filename, file_path,
                   duration_seconds, transcript, tfidf_keywords,
                   content_faiss_id, voice_faiss_id
            FROM audio_records
            WHERE content_faiss_id IN ({placeholders})
        """
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(sql, content_faiss_ids)
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Error as e:
            print(f'[DB][ERROR] get_record_by_faiss_ids thất bại: {e}')
            return []

    def get_records_by_voice_faiss_ids(self, voice_faiss_ids: list) -> list:
        self._ensure_connection()
        if not voice_faiss_ids or self.connection is None:
            return []
        placeholders = ', '.join(['%s'] * len(voice_faiss_ids))
        sql = f"""
            SELECT id, file_id, filename, file_path,
                   duration_seconds, transcript, tfidf_keywords,
                   content_faiss_id, voice_faiss_id
            FROM audio_records
            WHERE voice_faiss_id IN ({placeholders})
        """
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(sql, voice_faiss_ids)
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Error as e:
            print(f'[DB][ERROR] get_records_by_voice_faiss_ids thất bại: {e}')
            return []

    def count_records(self) -> int:
        self._ensure_connection()
        if self.connection is None:
            return 0
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT COUNT(*) FROM audio_records')
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Error:
            return 0

    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print('[DB] Đã đóng kết nối MySQL.')

