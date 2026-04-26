# -*- coding: utf-8 -*-
"""Tiện ích đổi tên file trong dataset về ASCII."""

import argparse
import os

from unidecode import unidecode


def rename_to_ascii(folder: str):
    files = os.listdir(folder)
    for filename in files:
        if filename.lower().endswith((".mp3", ".wav", ".flac", ".m4a", ".mp4")):
            ascii_name = unidecode(filename).replace(" ", "_")
            src = os.path.join(folder, filename)
            dst = os.path.join(folder, ascii_name)
            if src != dst:
                print(f"Renaming: {src} -> {dst}")
                os.rename(src, dst)
    print("Done.")


def parse_args():
    parser = argparse.ArgumentParser(description="Rename audio files to ASCII names.")
    parser.add_argument("--folder", required=True, help="Target folder containing audio files.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    rename_to_ascii(args.folder)

