from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import httpx
from yt_dlp import YoutubeDL

from app.core.config import settings


class YouTubeService:
    def __init__(self) -> None:
        self.timeout = settings.http_timeout_seconds

    @staticmethod
    def _pick_subtitle_track(
        subtitles: Dict[str, List[Dict[str, Any]]],
        language_priority: List[str],
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        for lang in language_priority:
            tracks = subtitles.get(lang) or subtitles.get(lang.lower()) or subtitles.get(lang.upper())
            if tracks:
                # Prefer webvtt
                vtt_track = next((t for t in tracks if t.get("ext") == "vtt"), None)
                return lang, (vtt_track or tracks[0])

        # fallback first available language
        if subtitles:
            first_lang = next(iter(subtitles.keys()))
            tracks = subtitles[first_lang]
            if tracks:
                vtt_track = next((t for t in tracks if t.get("ext") == "vtt"), None)
                return first_lang, (vtt_track or tracks[0])

        return None, None

    @staticmethod
    def _clean_vtt_text(raw: str) -> str:
        lines = raw.splitlines()
        kept: List[str] = []
        for line in lines:
            s = line.strip()
            if not s:
                continue
            if s.upper().startswith("WEBVTT"):
                continue
            if "-->" in s:
                continue
            if re.fullmatch(r"\d+", s):
                continue
            # remove simple html tags
            s = re.sub(r"<[^>]+>", "", s)
            kept.append(s)

        # de-duplicate consecutive duplicate lines
        deduped: List[str] = []
        prev = None
        for item in kept:
            if item != prev:
                deduped.append(item)
            prev = item

        return "\n".join(deduped).strip()

    async def _download_caption_text(self, caption_url: str) -> str:
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(caption_url)
            response.raise_for_status()
            return response.text

    async def extract(self, url: str, include_transcript: bool, language_priority: List[str]) -> Dict[str, Any]:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "noplaylist": True,
            "nocheckcertificate": True,
            "ignoreerrors": False,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            raise ValueError("Could not extract video information")

        # In rare cases extractor still returns playlist-like structures
        if info.get("_type") == "playlist":
            entries = info.get("entries") or []
            info = entries[0] if entries else info

        result: Dict[str, Any] = {
            "source_url": url,
            "video_id": info.get("id"),
            "title": info.get("title"),
            "description": info.get("description"),
            "uploader": info.get("uploader"),
            "channel": info.get("channel"),
            "duration_seconds": info.get("duration"),
            "upload_date": info.get("upload_date"),
            "chapters": info.get("chapters") or [],
            "tags": info.get("tags") or [],
            "transcript": None,
            "transcript_language": None,
            "transcript_source": None,
        }

        if not include_transcript:
            return result

        subtitles = info.get("subtitles") or {}
        automatic_captions = info.get("automatic_captions") or {}

        # Prefer manual subtitles, fallback to automatic captions
        lang, track = self._pick_subtitle_track(subtitles, language_priority)
        source = "manual"
        if not track:
            lang, track = self._pick_subtitle_track(automatic_captions, language_priority)
            source = "auto"

        if track and track.get("url"):
            raw_caption = await self._download_caption_text(track["url"])
            transcript = self._clean_vtt_text(raw_caption)
            result["transcript"] = transcript or None
            result["transcript_language"] = lang
            result["transcript_source"] = source

        return result
