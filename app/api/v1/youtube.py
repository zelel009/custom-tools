from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.db import create_youtube_job as db_create_youtube_job
from app.core.db import get_youtube_job
from app.models.schemas import (
    YouTubeExtractRequest,
    YouTubeExtractResponse,
    YouTubeJobCreateResponse,
    YouTubeJobStatusResponse,
)
from app.services.export_service import write_exports
from app.services.youtube_service import YouTubeService
from app.worker.queue import get_youtube_queue

router = APIRouter()
service = YouTubeService()


@router.post("/youtube/extract", response_model=YouTubeExtractResponse)
def extract_youtube_content(payload: YouTubeExtractRequest) -> YouTubeExtractResponse:
    try:
        data = service.extract(
            url=str(payload.url),
            include_transcript=payload.include_transcript,
            language_priority=payload.language_priority,
            max_items=payload.max_items,
        )

        export_files = write_exports(job_id=f"sync-{uuid4().hex}", result=data, formats=payload.export_formats)
        data["export_files"] = export_files

        return YouTubeExtractResponse(**data)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"YouTube extract failed: {exc}") from exc


@router.post("/youtube/jobs", response_model=YouTubeJobCreateResponse)
def create_youtube_job_endpoint(payload: YouTubeExtractRequest) -> YouTubeJobCreateResponse:
    job_id = str(uuid4())
    payload_data = payload.model_dump(mode="json")

    try:
        db_create_youtube_job(job_id=job_id, payload=payload_data, status="queued")
        q = get_youtube_queue()
        q.enqueue("app.worker.jobs.process_youtube_job", job_id, payload_data, job_id=job_id)
        return YouTubeJobCreateResponse(job_id=job_id, status="queued")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not queue YouTube job: {exc}") from exc


@router.get("/youtube/jobs/{job_id}", response_model=YouTubeJobStatusResponse)
def get_job_status(job_id: str) -> YouTubeJobStatusResponse:
    data = get_youtube_job(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="Job not found")

    result = None
    if data.get("result"):
        result = YouTubeExtractResponse(**{**data["result"], "export_files": data.get("export_files", {})})

    return YouTubeJobStatusResponse(
        job_id=data["job_id"],
        status=data["status"],
        result=result,
        error=data.get("error"),
        export_files=data.get("export_files", {}),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


@router.get("/youtube/jobs/{job_id}/exports/{fmt}")
def download_export(job_id: str, fmt: str):
    if fmt not in {"txt", "json", "srt"}:
        raise HTTPException(status_code=400, detail="Unsupported format")

    data = get_youtube_job(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="Job not found")

    file_path = data.get("export_files", {}).get(fmt)
    if not file_path:
        raise HTTPException(status_code=404, detail="Export file not available")

    p = Path(file_path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Export file missing on disk")

    media_type = {
        "txt": "text/plain",
        "json": "application/json",
        "srt": "application/x-subrip",
    }[fmt]

    return FileResponse(path=str(p), media_type=media_type, filename=f"{job_id}.{fmt}")
