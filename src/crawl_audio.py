# import yt_dlp
# import os
# import time

# def download_youtube_audio():
#     # 1. Cấu hình đường dẫn và danh sách mục tiêu
#     ffmpeg_path = r"E:\FFMPEG\bin"
#     output_base_dir = "Am_Thanh_Data"
#     metadata_file = "metadata.json"
    
#     targets = {
#         "https://www.youtube.com/@Sunhuynn/playlists": [
#             "đối nhân xử thế",
#             "Be the best version of yourself", 
#             "hoàn thiện bản thân"
#         # ],
#         # "https://www.youtube.com/@hieu-tv/playlists": [
#         #     "tự do tài chính cho người lãnh lương", 
#         #     "hành trình hiểu về bản thân", 
#         #     "tài chính cá nhân", 
#         #     "hành trình tự do tài chính", 
#         #     "kinh nghiệm sống"
#         ]
#     }

#     if os.path.exists(metadata_file):
#         with open(metadata_file, "r", encoding="utf-8") as f:
#             all_metadata = json.load(f)
#     else:
#         all_metadata = []




#     # 2. Đảm bảo thư mục gốc tồn tại
#     if not os.path.exists(output_base_dir):
#         os.makedirs(output_base_dir)

#     for channel_url, allowed_playlists in targets.items():
#         print(f"\n>>> Đang kiểm tra kênh: {channel_url}")
        
#         # Lấy thông tin playlist trước khi tải
#         ydl_gen_opts = {
#             'extract_flat': 'in_playlist',
#             'quiet': True,
#             'no_warnings': True,
#         }

#         with yt_dlp.YoutubeDL(ydl_gen_opts) as ydl:
#             try:
#                 channel_info = ydl.extract_info(channel_url, download=False)
#             except Exception as e:
#                 print(f"Lỗi khi truy cập kênh {channel_url}: {e}")
#                 continue
            
#             if 'entries' not in channel_info:
#                 print(f"Không tìm thấy danh sách phát nào.")
#                 continue

#             for playlist in channel_info['entries']:
#                 p_title = playlist.get('title', 'Unknown_Playlist')
                
#                 # Kiểm tra xem playlist có nằm trong danh sách yêu cầu không
#                 if any(target.lower() in p_title.lower() for target in allowed_playlists):
#                     print(f"\n[Bắt đầu tải] Danh sách phát: {p_title}")
                    
#                      with yt_dlp.YoutubeDL({'quiet': True}) as ydl_full:
#                         try:
#                             playlist_info = ydl_full.extract_info(playlist['url'], download=False)
#                         except Exception as e:
#                             print(f"Lỗi khi đọc playlist: {e}")
#                             continue

#                     if 'entries' not in playlist_info:
#                         continue

#                     # 👉 Duyệt từng video để lấy metadata
#                     for video in playlist_info['entries']:
#                         if not video:
#                             continue

#                         title = video.get("title")
#                         video_url = video.get("webpage_url")
#                         channel = video.get("uploader")
#                         upload_date = video.get("upload_date")

#                         # format lại ngày
#                         if upload_date:
#                             upload_date = datetime.strptime(upload_date, "%Y%m%d").strftime("%Y-%m-%d")

#                         metadata = {
#                             "title": title,
#                             "url": video_url,
#                             "channel": channel,
#                             "upload_date": upload_date,
#                             "playlist": p_title
#                         }

#                         all_metadata.append(metadata)

#                     # 3. Cấu hình chi tiết cho yt-dlp
#                     download_opts = {
#                         'format': 'bestaudio/best',
#                         'ffmpeg_location': ffmpeg_path,
                        
#                         # --- THÊM DÒNG NÀY ---
#                         'download_archive': 'download_archive.txt', 
#                         # ---------------------

#                         'postprocessors': [{
#                             'key': 'FFmpegExtractAudio',
#                             'preferredcodec': 'mp3',
#                             'preferredquality': '128', 
#                         }],
                        
#                         'postprocessor_args': [
#                             '-ac', '1',      
#                             '-ar', '16000'   
#                         ],
                        
#                         'outtmpl': f'{output_base_dir}/{p_title}/%(title)s.%(ext)s',
                        
#                         'match_filter': yt_dlp.utils.match_filter_func("duration > 62"),
#                         'sleep_interval': 10,
#                         'max_sleep_interval': 15,
#                         'ignoreerrors': True,
#                         'quiet': False,
#                         'no_warnings': False,
#                     }

#                     with yt_dlp.YoutubeDL(download_opts) as ydl_dl:
#                         try:
#                             ydl_dl.download([playlist['url']])
#                         except Exception as e:
#                             print(f"Lỗi khi tải playlist {p_title}: {e}")

#     with open(metadata_file, "w", encoding="utf-8") as f:
#         json.dump(all_metadata, f, ensure_ascii=False, indent=2)

#     print(f"\n>>> Đã lưu metadata vào {metadata_file}")
# if __name__ == "__main__":
#     print("Hệ thống bắt đầu thu thập dữ liệu âm thanh...")
#     download_youtube_audio()
#     print("\n>>> Hoàn thành tất cả tác vụ!")


import yt_dlp
import os
import json
from datetime import datetime

def download_youtube_audio():
    ffmpeg_path = r"D:\Slide 28 tech\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin"
    output_base_dir = "Am_Thanh_Data"
    metadata_file = "metadata.json" 
    
    targets = {
        "https://www.youtube.com/@Sunhuynn/playlists": [
            "đối nhân xử thế",
            # "Be the best version of yourself", 
            # "hoàn thiện bản thân"
        ]
#         # "https://www.youtube.com/@hieu-tv/playlists": [
#         #     "tự do tài chính cho người lãnh lương", 
#         #     "hành trình hiểu về bản thân", 
#         #     "tài chính cá nhân", 
#         #     "hành trình tự do tài chính", 
#         #     "kinh nghiệm sống"
#         ]
    }

    # Load metadata cũ
    if os.path.exists(metadata_file):
        with open(metadata_file, "r", encoding="utf-8") as f:
            all_metadata = json.load(f)
    else:
        all_metadata = []

    if not os.path.exists(output_base_dir):
        os.makedirs(output_base_dir)

    for channel_url, allowed_playlists in targets.items():
        print(f"\n>>> Đang kiểm tra kênh: {channel_url}")
        
        ydl_gen_opts = {
            'extract_flat': True,
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_gen_opts) as ydl:
            try:
                channel_info = ydl.extract_info(channel_url, download=False)
            except Exception as e:
                print(f"Lỗi khi truy cập kênh {channel_url}: {e}")
                continue
            
            if 'entries' not in channel_info:
                continue

            for playlist in channel_info['entries']:
                p_title = playlist.get('title', 'Unknown_Playlist')
                
                if any(t.lower() in p_title.lower() for t in allowed_playlists):
                    print(f"\n[Bắt đầu xử lý] Playlist: {p_title}")

                    # Lấy full info playlist
                    with yt_dlp.YoutubeDL({'quiet': True}) as ydl_full:
                        try:
                            playlist_info = ydl_full.extract_info(playlist['url'], download=False)
                        except Exception as e:
                            print(f"Lỗi khi đọc playlist: {e}")
                            continue

                    if 'entries' not in playlist_info:
                        continue

                    for video in playlist_info['entries']:
                        if not video:
                            continue

                        title = video.get("title")
                        video_url = video.get("webpage_url")
                        channel = video.get("uploader")
                        upload_date = video.get("upload_date")

                        if upload_date:
                            upload_date = datetime.strptime(upload_date, "%Y%m%d").strftime("%Y-%m-%d")

                        # tránh trùng
                        if any(m["url"] == video_url for m in all_metadata):
                            continue

                        metadata = {
                            "title": title,
                            "url": video_url,
                            "channel": channel,
                            "upload_date": upload_date,
                            "playlist": p_title
                        }

                        all_metadata.append(metadata)

                    # download audio
                    download_opts = {
                        'remote_components': 'ejs:github',
                        'format': 'bestaudio/best',
                        'ffmpeg_location': ffmpeg_path,
                        'js_runtimes': {
                            'node': {}
                        },
                        'download_archive': 'download_archive.txt',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '128',
                        }],
                        'postprocessor_args': [
                            '-ac', '1',
                            '-ar', '16000'
                        ],
                        'outtmpl': f'{output_base_dir}/{p_title}/%(title)s.%(ext)s',
                        'match_filter': yt_dlp.utils.match_filter_func("duration > 62"),
                        'ignoreerrors': True,
                        'quiet': False
                    }

                    with yt_dlp.YoutubeDL(download_opts) as ydl_dl:
                        try:
                            ydl_dl.download([playlist['url']])
                        except Exception as e:
                            print(f"Lỗi khi tải playlist {p_title}: {e}")

    #  lưu metadata
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, ensure_ascii=False, indent=2)

    print(f"\n>>> Đã lưu metadata vào {metadata_file}")


if __name__ == "__main__":
    print("Hệ thống bắt đầu thu thập dữ liệu âm thanh...")
    download_youtube_audio()
    print("\n>>> Hoàn thành tất cả tác vụ!")