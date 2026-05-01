# -*- coding: utf-8 -*-
"""Crawl YouTube playlists for Requirement-3 split-aware dataset."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Set

import yt_dlp


PLAYLIST_1 = "https://www.youtube.com/playlist?list=PLqHEScjKW63cjbytfP13k9qR9BNwZZNXn"
PLAYLIST_2 = "https://www.youtube.com/playlist?list=PL4JCp4qfxq-pGzGfn1CZ1MI9SYkNGwDgj"
PLAYLIST_3 = "https://www.youtube.com/playlist?list=PLi85pc7TdHuARtEHXP6GnFpDJHa3cA2-D"
PLAYLIST_4 = "https://www.youtube.com/playlist?list=PLyr6fSlXiFFYPTystHzlpdMymHrOiuW04"
PLAYLIST_5 = "https://www.youtube.com/playlist?list=PLnRl-W3gZI788VQFtD4eiegEPYdpyzPig"


@dataclass(frozen=True)
class PlaylistJob:
    playlist_url: str
    topic_id: str
    speaker_id: str
    split_role: str  # index | query_seen | query_unseen
    target_count: int


def _color(text: str, color_code: str) -> str:
    return f"\033[{color_code}m{text}\033[0m"


def _safe_ascii(value: str) -> str:
    text = (value or "").strip()
    text = re.sub(r"[^a-zA-Z0-9._-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "unknown"


def _render_table(title: str, rows: List[List[str]]):
    print(_color(f"\n{title}", "96"))
    if not rows:
        print(_color("(empty)", "90"))
        return
    widths = [max(len(str(row[i])) for row in rows) for i in range(len(rows[0]))]
    for idx, row in enumerate(rows):
        line = " | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row))
        if idx == 0:
            print(_color(line, "93"))
            print("-" * len(line))
        else:
            print(line)


def _make_youtube_watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def _iter_playlist_entries(playlist_url: str) -> List[Dict[str, str]]:
    opts = {"quiet": True, "extract_flat": True, "skip_download": True, "ignoreerrors": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
    entries = []
    for ent in info.get("entries", []) if info else []:
        if not ent:
            continue
        video_id = str(ent.get("id") or "").strip()
        if not video_id:
            continue
        entries.append(
            {
                "id": video_id,
                "url": _make_youtube_watch_url(video_id),
                "title": str(ent.get("title") or ""),
            }
        )
    return entries


def _read_existing_index(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_index(path: Path, rows: List[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "file_id",
        "file_name_original",
        "topic_id",
        "speaker_id",
        "duration",
        "split_role",
        "filepath",
        "playlist_url",
        "video_url",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        normalized_rows = [{k: row.get(k, "") for k in fieldnames} for row in rows]
        writer.writerows(normalized_rows)


def _load_metadata_json(path: Path) -> List[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_metadata_json(path: Path, rows: List[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def _duration_match_filter(min_duration_s: int, max_duration_s: int):
    def _filter(info_dict, *, incomplete=False):
        raw_duration = info_dict.get("duration")
        try:
            duration = float(raw_duration)
        except Exception:
            return "skip_missing_duration"
        if duration < float(min_duration_s):
            return "skip_too_short"
        if duration > float(max_duration_s):
            return "skip_too_long"
        return None

    return _filter


def _build_download_options(
    output_dir: Path,
    download_archive: Path,
    ffmpeg_path: str,
    min_duration_s: int,
    max_duration_s: int,
) -> dict:
    opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "noplaylist": True,
        "download_archive": str(download_archive),
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        "match_filter": _duration_match_filter(min_duration_s, max_duration_s),
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
        "postprocessor_args": ["-ar", "16000", "-ac", "1"],
    }
    if ffmpeg_path:
        opts["ffmpeg_location"] = ffmpeg_path
    return opts


def _download_single_video(
    video_url: str,
    output_dir: Path,
    download_archive: Path,
    ffmpeg_path: str,
    min_duration_s: int,
    max_duration_s: int,
    dry_run: bool,
) -> dict | None:
    if dry_run:
        return {
            "id": video_url.split("v=")[-1],
            "title": "dry_run_video",
            "duration": float(min_duration_s),
            "filepath": str((output_dir / f"{video_url.split('v=')[-1]}.wav").resolve()),
            "webpage_url": video_url,
            "uploader": "",
            "upload_date": "",
        }

    opts = _build_download_options(
        output_dir=output_dir,
        download_archive=download_archive,
        ffmpeg_path=ffmpeg_path,
        min_duration_s=min_duration_s,
        max_duration_s=max_duration_s,
    )
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
    if not info:
        return None
    if "entries" in info and info["entries"]:
        # Defensive path: noplaylist=True should avoid this.
        info = info["entries"][0]
    video_id = str(info.get("id") or "").strip()
    if not video_id:
        return None
    final_path = output_dir / f"{video_id}.wav"
    if not final_path.exists():
        return None
    duration = float(info.get("duration") or 0.0)
    return {
        "id": video_id,
        "title": str(info.get("title") or ""),
        "duration": duration,
        "filepath": str(final_path.resolve()),
        "webpage_url": str(info.get("webpage_url") or video_url),
        "uploader": str(info.get("uploader") or ""),
        "upload_date": str(info.get("upload_date") or ""),
    }


def _count_existing_for_job(rows: List[dict], job: PlaylistJob) -> int:
    count = 0
    for row in rows:
        if str(row.get("split_role", "")).strip() != job.split_role:
            continue
        if str(row.get("topic_id", "")).strip() != job.topic_id:
            continue
        if str(row.get("speaker_id", "")).strip() != job.speaker_id:
            continue
        if str(row.get("playlist_url", "")).strip() != job.playlist_url:
            continue
        if str(row.get("file_id", "")).strip():
            count += 1
    return count


def _job_output_dir(output_root: Path, job: PlaylistJob) -> Path:
    topic_folder = _safe_ascii(job.topic_id)
    speaker_folder = _safe_ascii(job.speaker_id)
    split_name = "Index" if job.split_role == "index" else ("Test_Seen" if job.split_role == "query_seen" else "Test_Unseen")
    return output_root / split_name / topic_folder / speaker_folder


def _count_existing_wavs_for_job(output_root: Path, job: PlaylistJob) -> int:
    output_dir = _job_output_dir(output_root, job)
    if not output_dir.exists():
        return 0
    return len(list(output_dir.glob("*.wav")))


def _collect_job(
    job: PlaylistJob,
    output_root: Path,
    archive_file: Path,
    ffmpeg_path: str,
    min_duration_s: int,
    max_duration_s: int,
    used_video_ids: Set[str],
    dry_run: bool,
    existing_count: int,
    on_accept: Callable[[dict], None] | None = None,
) -> List[dict]:
    output_dir = _job_output_dir(output_root, job)
    output_dir.mkdir(parents=True, exist_ok=True)

    remaining_target = max(0, job.target_count - existing_count)
    print(
        _color(
            f"\n[START] {job.split_role} | {job.topic_id} | {job.speaker_id} | "
            f"existing={existing_count} target={job.target_count} remaining={remaining_target}",
            "94",
        )
    )
    if remaining_target == 0:
        print(_color(f"[DONE] {job.split_role} already satisfied target.", "96"))
        return []

    entries = _iter_playlist_entries(job.playlist_url)
    if not entries:
        print(_color(f"[WARN] No entries: {job.playlist_url}", "91"))
        return []

    accepted_rows: List[dict] = []
    for ent in entries:
        if len(accepted_rows) >= remaining_target:
            break
        video_id = ent["id"]
        if video_id in used_video_ids:
            continue
        result = _download_single_video(
            video_url=ent["url"],
            output_dir=output_dir,
            download_archive=archive_file,
            ffmpeg_path=ffmpeg_path,
            min_duration_s=min_duration_s,
            max_duration_s=max_duration_s,
            dry_run=dry_run,
        )
        if not result:
            continue
        used_video_ids.add(video_id)
        row = {
            "file_id": video_id,
            "file_name_original": result["title"],
            "topic_id": job.topic_id,
            "speaker_id": job.speaker_id,
            "duration": round(float(result["duration"]), 3),
            "split_role": job.split_role,
            "filepath": result["filepath"],
            "playlist_url": job.playlist_url,
            "video_url": result["webpage_url"],
        }
        accepted_rows.append(row)
        if on_accept is not None:
            on_accept(row)
        print(
            _color(
                f"[OK] {job.split_role} +{len(accepted_rows)}/{remaining_target} "
                f"(total={existing_count + len(accepted_rows)}/{job.target_count}): "
                f"{video_id} ({row['duration']}s)",
                "92",
            )
        )

    print(
        _color(
            f"[DONE] {job.split_role} | new={len(accepted_rows)} | "
            f"final_total={existing_count + len(accepted_rows)}/{job.target_count}",
            "96",
        )
    )
    return accepted_rows


def _default_jobs(max_index_per_playlist: int, max_unseen_per_playlist: int, max_seen_total: int) -> List[PlaylistJob]:
    jobs: List[PlaylistJob] = []
    # query_seen first to guarantee exclusion from index.
    jobs.extend(
        [
            PlaylistJob(PLAYLIST_1, "PhatGiao", "SuThanhMinh", "query_seen", max_seen_total),
        ]
    )
    jobs.extend(
        [
            PlaylistJob(PLAYLIST_3, "GiaoDuc_TapDoc", "GiaoVien1", "query_unseen", max_unseen_per_playlist),
            PlaylistJob(PLAYLIST_4, "GiaoDuc_Toan", "GiaoVien2", "query_unseen", max_unseen_per_playlist),
            PlaylistJob(PLAYLIST_5, "GiaoDuc_VatLy", "GiaoVien3", "query_unseen", max_unseen_per_playlist),
        ]
    )
    jobs.extend(
        [
            PlaylistJob(PLAYLIST_1, "PhatGiao", "SuThanhMinh", "index", max_index_per_playlist),
            PlaylistJob(PLAYLIST_2, "PhatGiao", "SuVanDap", "index", max_index_per_playlist),
        ]
    )
    return jobs


def parse_args():
    parser = argparse.ArgumentParser(description="Stage1 crawler for Requirement-3 split dataset.")
    parser.add_argument("--output-root", default="src/Processed_Audio_Data")
    parser.add_argument("--index-csv", default="src/artifacts/stage1/dataset_index.csv")
    parser.add_argument("--metadata-json", default="src/artifacts/stage1/metadata.json")
    parser.add_argument("--download-archive", default=os.getenv("YT_DOWNLOAD_ARCHIVE", "src/artifacts/stage1/download_archive.txt"))
    parser.add_argument("--ffmpeg-path", default=os.getenv("FFMPEG_PATH", ""))
    parser.add_argument("--min-duration-s", type=int, default=60)
    parser.add_argument("--max-duration-s", type=int, default=900)
    parser.add_argument("--max-index-per-playlist", type=int, default=250)
    parser.add_argument("--max-unseen-per-playlist", type=int, default=3)
    parser.add_argument("--max-seen-total", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    output_root = Path(args.output_root)
    index_csv = Path(args.index_csv)
    metadata_json = Path(args.metadata_json)
    archive_file = Path(args.download_archive)
    archive_file.parent.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)

    if args.min_duration_s >= args.max_duration_s:
        raise ValueError("min-duration-s must be < max-duration-s")

    existing_rows = _read_existing_index(index_csv)
    used_video_ids: Set[str] = {str(r.get("file_id", "")).strip() for r in existing_rows if r.get("file_id")}
    metadata_rows = _load_metadata_json(metadata_json)
    metadata_by_url = {str(r.get("url", "")): r for r in metadata_rows if r.get("url")}
    merged_rows = list(existing_rows)

    def _persist_state():
        _write_index(index_csv, merged_rows)
        _save_metadata_json(metadata_json, list(metadata_by_url.values()))

    jobs = _default_jobs(
        max_index_per_playlist=args.max_index_per_playlist,
        max_unseen_per_playlist=args.max_unseen_per_playlist,
        max_seen_total=args.max_seen_total,
    )

    new_rows: List[dict] = []
    for job in jobs:
        existing_csv_count = _count_existing_for_job(merged_rows, job)
        existing_wav_count = _count_existing_wavs_for_job(output_root, job)
        existing_count = max(existing_csv_count, existing_wav_count)

        def _on_accept(row: dict):
            merged_rows.append(row)
            video_url = row["video_url"]
            if video_url not in metadata_by_url:
                metadata_by_url[video_url] = {
                    "title": row["file_name_original"],
                    "url": video_url,
                    "channel": row["speaker_id"],
                    "playlist": row["topic_id"],
                    "split_role": row["split_role"],
                    "duration": row["duration"],
                }
            _persist_state()

        collected = _collect_job(
            job=job,
            output_root=output_root,
            archive_file=archive_file,
            ffmpeg_path=args.ffmpeg_path,
            min_duration_s=args.min_duration_s,
            max_duration_s=args.max_duration_s,
            used_video_ids=used_video_ids,
            dry_run=args.dry_run,
            existing_count=existing_count,
            on_accept=_on_accept,
        )
        new_rows.extend(collected)

    _persist_state()

    split_counts: Dict[str, int] = {"index": 0, "query_seen": 0, "query_unseen": 0}
    for row in new_rows:
        split = row["split_role"]
        split_counts[split] = split_counts.get(split, 0) + 1

    table = [
        ["Metric", "Value"],
        ["New index rows", str(split_counts.get("index", 0))],
        ["New query_seen rows", str(split_counts.get("query_seen", 0))],
        ["New query_unseen rows", str(split_counts.get("query_unseen", 0))],
        ["New total rows", str(len(new_rows))],
        ["Dataset index", str(index_csv)],
        ["Metadata json", str(metadata_json)],
    ]
    _render_table("CRAWL SUMMARY", table)
    print(_color("\n[DONE] Stage1 crawl pipeline completed.", "92"))


if __name__ == "__main__":
    main()
