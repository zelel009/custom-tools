from __future__ import annotations

from typing import Any

from app.core.db import update_youtube_job
from app.services.export_service import write_exports
from app.services.youtube_service import YouTubeService


def process_youtube_job(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    service = YouTubeService()
    update_youtube_job(job_id, status="running", error_text=None)

    try:
        result = service.extract(
            url=payload["url"],
            include_transcript=payload.get("include_transcript", True),
            language_priority=payload.get("language_priority", ["vi", "en"]),
            max_items=payload.get("max_items", 10),
        )
        export_formats = payload.get("export_formats", ["json"])
        export_files = write_exports(job_id=job_id, result=result, formats=export_formats)

        update_youtube_job(
            job_id,
            status="completed",
            result=result,
            export_files=export_files,
            error_text=None,
        )
        return {"job_id": job_id, "status": "completed", "export_files": export_files}

    except Exception as exc:
        update_youtube_job(job_id, status="failed", error_text=str(exc))
        raise
