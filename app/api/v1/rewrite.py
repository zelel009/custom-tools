from fastapi import APIRouter, HTTPException

from app.core.db import insert_rewrite_run
from app.models.schemas import RewriteComparison, RewriteRequest, RewriteResponse, RewriteVariant
from app.services.rewrite_service import RewriteService

router = APIRouter()
service = RewriteService()


def _text_stats(text: str, preserve_keywords: list[str]) -> tuple[int, int, list[str]]:
    words = len([w for w in text.split() if w.strip()])
    chars = len(text)
    lowered = text.lower()
    present = [kw for kw in preserve_keywords if kw.lower() in lowered]
    return words, chars, present


@router.post("/rewrite", response_model=RewriteResponse)
async def rewrite_content(payload: RewriteRequest) -> RewriteResponse:
    try:
        raw_variants, model_used, fallback_used = await service.rewrite(
            text=payload.text,
            style=payload.style,
            language=payload.language,
            preserve_keywords=payload.preserve_keywords,
            variant_count=payload.variant_count,
        )

        variants: list[RewriteVariant] = []
        for v in raw_variants:
            word_count, char_count, present = _text_stats(v["text"], payload.preserve_keywords)
            variants.append(
                RewriteVariant(
                    index=v["index"],
                    style=v["style"],
                    text=v["text"],
                    word_count=word_count,
                    char_count=char_count,
                    preserved_keywords=present,
                )
            )

        original_word_count = len([w for w in payload.text.split() if w.strip()])
        original_char_count = len(payload.text)

        comparison = RewriteComparison(
            original_word_count=original_word_count,
            original_char_count=original_char_count,
            variants_summary=[
                {
                    "index": v.index,
                    "style": v.style,
                    "word_count": v.word_count,
                    "char_count": v.char_count,
                    "preserved_keywords_count": len(v.preserved_keywords),
                }
                for v in variants
            ],
        )

        response = RewriteResponse(
            model_used=model_used,
            fallback_used=fallback_used,
            variants=variants,
            comparison=comparison,
        )

        insert_rewrite_run(request_data=payload.model_dump(), response_data=response.model_dump())
        return response

    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Rewrite failed: {exc}") from exc
