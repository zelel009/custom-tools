from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx
from yt_dlp import YoutubeDL

from app.core.config import settings


@dataclass
class CaptionResult:
    transcript_text: Optional[str]
    transcript_language: Optional[str]
    transcript_source: Optional[str]
    transcript_srt: Optional[str]
    transcript_segments: List[dict]


class YouTubeService:
    def __init__(self) -> None:
        self.timeout = settings.http_timeout_seconds

    @staticmethod
    def _pick_subtitle_track(
        subtitles: Dict[str, List[Dict[str, Any]]],
        language_priority: List[str],
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        def choose_track(tracks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
            for ext in ("srt", "vtt", "json3"):
                chosen = next((t for t in tracks if t.get("ext") == ext), None)
                if chosen:
                    return chosen
            return tracks[0] if tracks else None

        for lang in language_priority:
            tracks = subtitles.get(lang) or subtitles.get(lang.lower()) or subtitles.get(lang.upper())
            if tracks:
                return lang, choose_track(tracks)

        if subtitles:
            first_lang = next(iter(subtitles.keys()))
            tracks = subtitles[first_lang]
            return first_lang, choose_track(tracks)

        return None, None

    @staticmethod
    def _to_srt_timestamp(seconds: float) -> str:
        ms = int(round(seconds * 1000))
        td = timedelta(milliseconds=ms)
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        millis = ms % 1000
        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

    @staticmethod
    def _parse_vtt_segments(raw: str) -> List[dict]:
        segments: List[dict] = []
        blocks = re.split(r"\n\s*\n", raw.replace("\r\n", "\n"))

        for block in blocks:
            lines = [line.strip() for line in block.split("\n") if line.strip()]
            if not lines:
                continue
            if lines[0].upper().startswith("WEBVTT"):
                continue

            timing_idx = None
            for i, line in enumerate(lines):
                if "-->" in line:
                    timing_idx = i
                    break
            if timing_idx is None:
                continue

            timing = lines[timing_idx]
            text_lines = lines[timing_idx + 1 :]
            if not text_lines:
                continue

            parts = timing.split("-->")
            if len(parts) != 2:
                continue

            def parse_time(value: str) -> float:
                clean = value.strip().split(" ")[0].replace(",", ".")
                hhmmss = clean.split(":")
                if len(hhmmss) == 3:
                    h, m, s = hhmmss
                elif len(hhmmss) == 2:
                    h, m, s = "0", hhmmss[0], hhmmss[1]
                else:
                    return 0.0
                return int(h) * 3600 + int(m) * 60 + float(s)

            start = parse_time(parts[0])
            end = parse_time(parts[1])
            text = html.unescape(re.sub(r"<[^>]+>", "", " ".join(text_lines))).strip()
            if text:
                segments.append({"start": start, "end": end, "text": text})

        return segments

    @classmethod
    def _segments_to_srt(cls, segments: List[dict]) -> str:
        lines: List[str] = []
        for idx, seg in enumerate(segments, start=1):
            lines.append(str(idx))
            lines.append(f"{cls._to_srt_timestamp(seg['start'])} --> {cls._to_srt_timestamp(seg['end'])}")
            lines.append(seg["text"])
            lines.append("")
        return "\n".join(lines).strip()

    @staticmethod
    def _clean_transcript_text(text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", text)
        lines = [ln.strip() for ln in text.splitlines()]
        deduped: List[str] = []
        prev = None
        for line in lines:
            if not line:
                continue
            if line != prev:
                deduped.append(line)
            prev = line
        return "\n".join(deduped).strip()

    def _download_caption_text(self, caption_url: str) -> str:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(caption_url)
            response.raise_for_status()
            return response.text

    def _extract_caption(self, info: dict, language_priority: List[str]) -> CaptionResult:
        subtitles = info.get("subtitles") or {}
        automatic_captions = info.get("automatic_captions") or {}

        lang, track = self._pick_subtitle_track(subtitles, language_priority)
        source = "manual"
        if not track:
            lang, track = self._pick_subtitle_track(automatic_captions, language_priority)
            source = "auto"

        if not track or not track.get("url"):
            return CaptionResult(None, None, None, None, [])

        raw = self._download_caption_text(track["url"])
        ext = track.get("ext", "").lower()

        segments: List[dict] = []
        transcript_srt: Optional[str] = None

        if ext == "srt":
            transcript_srt = raw.strip()
            # best effort plain text extraction
            cleaned = re.sub(r"\d+\n", "", transcript_srt)
            cleaned = re.sub(r"\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+\d{2}:\d{2}:\d{2},\d{3}", "", cleaned)
            transcript_text = self._clean_transcript_text(cleaned)
        else:
            segments = self._parse_vtt_segments(raw)
            if segments:
                transcript_text = self._clean_transcript_text("\n".join(seg["text"] for seg in segments))
                transcript_srt = self._segments_to_srt(segments)
            else:
                transcript_text = self._clean_transcript_text(raw)

        return CaptionResult(
            transcript_text=transcript_text or None,
            transcript_language=lang,
            transcript_source=source,
            transcript_srt=transcript_srt,
            transcript_segments=segments,
        )

    @staticmethod
    def _normalize_item(info: dict, caption: Optional[CaptionResult] = None) -> Dict[str, Any]:
        return {
            "source_url": info.get("webpage_url") or info.get("original_url") or info.get("url"),
            "video_id": info.get("id"),
            "title": info.get("title"),
            "description": info.get("description"),
            "uploader": info.get("uploader"),
            "channel": info.get("channel"),
            "duration_seconds": info.get("duration"),
            "upload_date": info.get("upload_date"),
            "chapters": info.get("chapters") or [],
            "tags": info.get("tags") or [],
            "transcript": caption.transcript_text if caption else None,
            "transcript_language": caption.transcript_language if caption else None,
            "transcript_source": caption.transcript_source if caption else None,
            # internal fields used for export building
            "_transcript_srt": caption.transcript_srt if caption else None,
            "_transcript_segments": caption.transcript_segments if caption else [],
        }

    def extract(self, url: str, include_transcript: bool, language_priority: List[str], max_items: int) -> Dict[str, Any]:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "noplaylist": False,
            "nocheckcertificate": True,
            "ignoreerrors": True,
            "extract_flat": False,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            raise ValueError("Could not extract content from URL")

        result_items: List[Dict[str, Any]] = []

        if info.get("_type") == "playlist":
            entries = [e for e in (info.get("entries") or []) if e][:max_items]
            for entry in entries:
                entry_url = entry.get("webpage_url") or entry.get("url")
                if not entry_url:
                    continue

                with YoutubeDL(ydl_opts) as ydl:
                    video_info = ydl.extract_info(entry_url, download=False)
                if not video_info:
                    continue

                caption = self._extract_caption(video_info, language_priority) if include_transcript else None
                result_items.append(self._normalize_item(video_info, caption))

            return {
                "kind": "playlist",
                "source_url": url,
                "item_count": len(result_items),
                "items": result_items,
            }

        caption = self._extract_caption(info, language_priority) if include_transcript else None
        result_items.append(self._normalize_item(info, caption))

        return {
            "kind": "video",
            "source_url": url,
            "item_count": len(result_items),
            "items": result_items,
        }
