# -*- coding: utf-8 -*-
"""Thu thập danh sách file và metadata cho Giai đoạn 1."""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def collect_audio_files(input_dir: Path, allowed_exts: Tuple[str, ...]) -> List[Path]:
    files: List[Path] = []
    for root, _, names in os.walk(input_dir):
        for name in names:
            p = Path(root) / name
            if p.suffix.lower() in allowed_exts:
                files.append(p)
    return sorted(files)


def infer_topic_speaker(input_dir: Path, audio_path: Path, layout: str = "speaker_topic") -> Tuple[str, str]:
    """
    Quy ước thư mục ưu tiên:
    raw_data/speaker_id/topic_id/file.ext
    """
    rel = audio_path.relative_to(input_dir)
    parts = rel.parts[:-1]
    if len(parts) >= 2:
        first = parts[0].strip()
        second = parts[1].strip()
        if layout == "topic_speaker":
            topic_id = first or "unknown_topic"
            speaker_id = second or "unknown_speaker"
        else:
            speaker_id = first or "unknown_speaker"
            topic_id = second or "unknown_topic"
        return topic_id, speaker_id
    if len(parts) == 1:
        return parts[0].strip() or "unknown_topic", "unknown_speaker"
    return "unknown_topic", "unknown_speaker"


def load_metadata_map(metadata_path: Path) -> Dict[str, dict]:
    if not metadata_path.exists():
        return {}
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            rows = json.load(f)
    except Exception:
        return {}

    mapping: Dict[str, dict] = {}
    for item in rows:
        title = normalize_text(str(item.get("title", "")))
        if title:
            mapping[title] = item
    return mapping


def match_source_by_filename(audio_path: Path, metadata_map: Dict[str, dict]) -> dict:
    key = normalize_text(audio_path.stem)
    if not key:
        return {}
    if key in metadata_map:
        return metadata_map[key]
    for title_key, item in metadata_map.items():
        if key in title_key or title_key in key:
            return item
    return {}
