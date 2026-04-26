# -*- coding: utf-8 -*-
"""Demo nhanh cho content extractor Stage 2."""

import os

from stage2.content_feature_extractor import ContentFeatureExtractor


def main():
    extractor = ContentFeatureExtractor()
    audio_path = os.path.join(
        "src",
        "Processed_Audio_Data",
        "ĐỐI NHÂN XỬ THẾ",
        "5_tips_ung_xu_giao_tiep_ban_nen_biet.wav",
    )
    print(f"Testing file: {audio_path}")
    print(f"File exists: {os.path.exists(audio_path)}")
    transcript = extractor.transcribe_audio(audio_path)
    print("Transcript length:", len(transcript))
    print("First 200 chars:", transcript[:200])


if __name__ == "__main__":
    main()
