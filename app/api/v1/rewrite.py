from fastapi import APIRouter, HTTPException

from app.models.schemas import RewriteRequest, RewriteResponse
from app.services.rewrite_service import RewriteService

router = APIRouter()
service = RewriteService()


@router.post("/rewrite", response_model=RewriteResponse)
async def rewrite_content(payload: RewriteRequest) -> RewriteResponse:
    try:
        rewritten_text, model_used, fallback_used = await service.rewrite(
            text=payload.text,
            style=payload.style,
            language=payload.language,
            preserve_keywords=payload.preserve_keywords,
        )
        return RewriteResponse(
            rewritten_text=rewritten_text,
            model_used=model_used,
            fallback_used=fallback_used,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Rewrite failed: {exc}") from exc
