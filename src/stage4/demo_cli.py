# -*- coding: utf-8 -*-
"""Giai đoạn 4 — CLI demo: một file âm thanh vào, hai cột kết quả (Top-3 nội dung | Top-3 giọng)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from stage3.retrieval_top3 import run_query


def parse_args():
    p = argparse.ArgumentParser(description="Demo CLI — top-3 content và top-3 voice.")
    p.add_argument("audio_path", help="Đường dẫn file âm thanh truy vấn (.wav)")
    p.add_argument("--sqlite-db", default="src/artifacts/stage3/audio_hybrid.db")
    p.add_argument("--content-index", default="src/artifacts/stage3/content.index")
    p.add_argument("--voice-index", default="src/artifacts/stage3/voice.index")
    p.add_argument("--top-k", type=int, default=3)
    p.add_argument("--whisper-model", default="tiny")
    p.add_argument("--stt-max-duration-s", type=float, default=90.0)
    p.add_argument("--voice-max-duration-s", type=float, default=90.0)
    p.add_argument("--output-log", default="src/artifacts/stage3/demo_last_query.json")
    return p.parse_args()


def print_two_columns(content_rows: list, voice_rows: list) -> None:
    cw = 52
    kc = len(content_rows)
    kv = len(voice_rows)
    print("\n" + "=" * (cw * 2 + 3))
    left_title = f"TOP-{kc} NOI DUNG (giam dan similarity)"
    right_title = f"TOP-{kv} GIONG NOI"
    print(f"{left_title:<{cw}} | {right_title}")
    print("=" * (cw * 2 + 3))
    n = max(len(content_rows), len(voice_rows))
    for i in range(n):
        left = ""
        if i < len(content_rows):
            r = content_rows[i]
            left = f'{r["rank"]}. [{r["similarity"]:.4f}] {r["file_name"]}'
        right = ""
        if i < len(voice_rows):
            r = voice_rows[i]
            right = f'{r["rank"]}. [{r["similarity"]:.4f}] {r["file_name"]}'
        print(f"{left:<{cw}} | {right}")
    print("=" * (cw * 2 + 3) + "\n")


def main():
    args = parse_args()
    out = run_query(
        query_audio=Path(args.audio_path),
        sqlite_db=Path(args.sqlite_db),
        content_index_path=Path(args.content_index),
        voice_index_path=Path(args.voice_index),
        top_k=args.top_k,
        whisper_model=args.whisper_model,
        stt_max_duration_s=args.stt_max_duration_s,
        voice_max_duration_s=args.voice_max_duration_s,
        output_log=Path(args.output_log),
        verbose=False,
    )
    print_two_columns(out.get("content_top3") or [], out.get("voice_top3") or [])


if __name__ == "__main__":
    main()
