# -*- coding: utf-8 -*-
"""Thu thập dữ liệu âm thanh cho Giai đoạn 1 bằng yt-dlp."""

import json
import os
from datetime import datetime

import yt_dlp


def _safe_name(text: str) -> str:
    text = (text or "").strip().replace("/", "_").replace("\\", "_")
    banned = ':*?"<>|'
    for ch in banned:
        text = text.replace(ch, "_")
    return text[:120] if text else "unknown"


def download_youtube_audio():
    ffmpeg_path = os.getenv("FFMPEG_PATH", "").strip()
    output_base_dir = os.getenv("AUDIO_OUTPUT_DIR", "Am_Thanh_Data")
    metadata_file = os.getenv("CRAWL_METADATA_FILE", "src/artifacts/stage1/metadata.json")
    download_archive = os.getenv("YT_DOWNLOAD_ARCHIVE", "src/artifacts/stage1/download_archive.txt")

    targets = {
        "https://www.youtube.com/@Sunhuynn/playlists": [
            "đối nhân xử thế",
            # "Be the best version of yourself",
            # "hoàn thiện bản thân",
        ]
    }

    os.makedirs(os.path.dirname(metadata_file), exist_ok=True)

    if os.path.exists(metadata_file):
        with open(metadata_file, "r", encoding="utf-8") as f:
            all_metadata = json.load(f)
    else:
        all_metadata = []

    os.makedirs(output_base_dir, exist_ok=True)

    for channel_url, allowed_playlists in targets.items():
        print(f"\n>>> Đang kiểm tra kênh: {channel_url}")

        ydl_gen_opts = {
            "extract_flat": True,
            "quiet": True,
            "no_warnings": True,
        }

        with yt_dlp.YoutubeDL(ydl_gen_opts) as ydl:
            try:
                channel_info = ydl.extract_info(channel_url, download=False)
            except Exception as e:
                print(f"Lỗi khi truy cập kênh {channel_url}: {e}")
                continue

            if "entries" not in channel_info:
                continue

            for playlist in channel_info["entries"]:
                p_title = playlist.get("title", "Unknown_Playlist")

                if any(t.lower() in p_title.lower() for t in allowed_playlists):
                    print(f"\n[Bắt đầu xử lý] Playlist: {p_title}")

                    with yt_dlp.YoutubeDL({"quiet": True}) as ydl_full:
                        try:
                            playlist_info = ydl_full.extract_info(playlist["url"], download=False)
                        except Exception as e:
                            print(f"Lỗi khi đọc playlist: {e}")
                            continue

                    if "entries" not in playlist_info:
                        continue

                    for video in playlist_info["entries"]:
                        if not video:
                            continue

                        title = video.get("title")
                        video_url = video.get("webpage_url")
                        channel = video.get("uploader")
                        upload_date = video.get("upload_date")

                        if upload_date:
                            upload_date = datetime.strptime(upload_date, "%Y%m%d").strftime("%Y-%m-%d")

                        if any(m.get("url") == video_url for m in all_metadata):
                            continue

                        all_metadata.append(
                            {
                                "title": title,
                                "url": video_url,
                                "channel": channel,
                                "upload_date": upload_date,
                                "playlist": p_title,
                            }
                        )

                    channel_name = _safe_name(playlist_info.get("uploader") or "unknown_speaker")
                    topic_name = _safe_name(p_title)

                    download_opts = {
                        "remote_components": "ejs:github",
                        "format": "bestaudio/best",
                        "js_runtimes": {"node": {}},
                        "download_archive": download_archive,
                        "postprocessors": [
                            {
                                "key": "FFmpegExtractAudio",
                                "preferredcodec": "mp3",
                                "preferredquality": "128",
                            }
                        ],
                        "postprocessor_args": ["-ac", "1", "-ar", "16000"],
                        # Đồng bộ với parser label mặc định: speaker/topic/file
                        "outtmpl": f"{output_base_dir}/{channel_name}/{topic_name}/%(title)s.%(ext)s",
                        "match_filter": yt_dlp.utils.match_filter_func("duration > 62"),
                        "ignoreerrors": True,
                        "quiet": False,
                    }
                    if ffmpeg_path:
                        download_opts["ffmpeg_location"] = ffmpeg_path

                    with yt_dlp.YoutubeDL(download_opts) as ydl_dl:
                        try:
                            ydl_dl.download([playlist["url"]])
                        except Exception as e:
                            print(f"Lỗi khi tải playlist {p_title}: {e}")

    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, ensure_ascii=False, indent=2)

    print(f"\n>>> Đã lưu metadata vào {metadata_file}")


if __name__ == "__main__":
    print("Hệ thống bắt đầu thu thập dữ liệu âm thanh...")
    download_youtube_audio()
    print("\n>>> Hoàn thành tất cả tác vụ!")
