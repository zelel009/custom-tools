from fastapi import APIRouter, HTTPException

from app.models.schemas import YouTubeExtractRequest, YouTubeExtractResponse
from app.services.youtube_service import YouTubeService

router = APIRouter()
service = YouTubeService()


@router.post("/youtube/extract", response_model=YouTubeExtractResponse)
async def extract_youtube_content(payload: YouTubeExtractRequest) -> YouTubeExtractResponse:
    try:
        data = await service.extract(
            url=str(payload.url),
            include_transcript=payload.include_transcript,
            language_priority=payload.language_priority,
        )
        return YouTubeExtractResponse(**data)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"YouTube extract failed: {exc}") from exc
