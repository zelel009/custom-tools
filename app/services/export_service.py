from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.core.config import settings


def _to_srt_timestamp(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02}:{m:02}:{s:02},000"


def _naive_transcript_to_srt(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out: List[str] = []
    start = 0
    for idx, line in enumerate(lines, start=1):
        end = start + 2
        out.append(str(idx))
        out.append(f"{_to_srt_timestamp(start)} --> {_to_srt_timestamp(end)}")
        out.append(line)
        out.append("")
        start = end
    return "\n".join(out).strip()


def _build_txt_content(result: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"Kind: {result.get('kind')}")
    lines.append(f"Source URL: {result.get('source_url')}")
    lines.append(f"Item count: {result.get('item_count')}")
    lines.append("=" * 60)

    for idx, item in enumerate(result.get("items", []), start=1):
        lines.append(f"[{idx}] {item.get('title') or '(no title)'}")
        lines.append(f"Video ID: {item.get('video_id')}")
        lines.append(f"Channel: {item.get('channel')}")
        lines.append(f"Duration: {item.get('duration_seconds')} sec")
        lines.append(f"Upload date: {item.get('upload_date')}")
        lines.append(f"URL: {item.get('source_url')}")
        lines.append(f"Description: {item.get('description') or ''}")
        lines.append("")
        lines.append("Transcript:")
        lines.append(item.get("transcript") or "(no transcript)")
        lines.append("-" * 60)

    return "\n".join(lines).strip()


def _build_srt_content(result: Dict[str, Any]) -> str:
    out_lines: List[str] = []
    current_index = 1

    for item_idx, item in enumerate(result.get("items", []), start=1):
        item_srt = item.get("_transcript_srt")
        transcript_text = item.get("transcript") or ""

        if item_srt:
            chunks = [blk for blk in item_srt.replace("\r\n", "\n").split("\n\n") if blk.strip()]
            out_lines.append(f"NOTE Item {item_idx}: {item.get('title') or ''}")
            out_lines.append("")
            for chunk in chunks:
                lines = [ln for ln in chunk.split("\n") if ln.strip()]
                if len(lines) >= 2:
                    timing = lines[1] if "-->" in lines[1] else (lines[0] if "-->" in lines[0] else None)
                    text_lines = lines[2:] if timing == lines[1] else lines[1:]
                    if timing:
                        out_lines.append(str(current_index))
                        out_lines.append(timing)
                        out_lines.extend(text_lines)
                        out_lines.append("")
                        current_index += 1
            continue

        if transcript_text:
            naive = _naive_transcript_to_srt(transcript_text)
            chunks = [blk for blk in naive.split("\n\n") if blk.strip()]
            out_lines.append(f"NOTE Item {item_idx}: {item.get('title') or ''}")
            out_lines.append("")
            for chunk in chunks:
                lines = [ln for ln in chunk.split("\n") if ln.strip()]
                if len(lines) >= 3:
                    out_lines.append(str(current_index))
                    out_lines.append(lines[1])
                    out_lines.extend(lines[2:])
                    out_lines.append("")
                    current_index += 1

    return "\n".join(out_lines).strip()


def write_exports(job_id: str, result: Dict[str, Any], formats: List[str]) -> Dict[str, str]:
    export_root = Path(settings.export_dir)
    export_root.mkdir(parents=True, exist_ok=True)

    job_dir = export_root / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    export_files: Dict[str, str] = {}

    if "json" in formats:
        p = job_dir / "output.json"
        p.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        export_files["json"] = str(p)

    if "txt" in formats:
        p = job_dir / "output.txt"
        p.write_text(_build_txt_content(result), encoding="utf-8")
        export_files["txt"] = str(p)

    if "srt" in formats:
        p = job_dir / "output.srt"
        p.write_text(_build_srt_content(result), encoding="utf-8")
        export_files["srt"] = str(p)

    return export_files
