from __future__ import annotations

from typing import List

import httpx

from app.core.config import settings
from app.models.schemas import RewriteStyle


class RewriteService:
    def __init__(self) -> None:
        self.api_key = settings.gemini_api_key.strip()
        self.model = settings.gemini_model
        self.timeout = settings.http_timeout_seconds

    def _build_prompt(self, text: str, style: str, language: str, preserve_keywords: List[str], variant_idx: int) -> str:
        keywords_line = ", ".join(preserve_keywords) if preserve_keywords else "(none)"
        return (
            f"Rewrite the following content in {language}.\\n"
            f"Style: {style}.\\n"
            f"This is variant #{variant_idx}. Make it meaningfully different from other variants.\\n"
            "Keep original meaning, facts, names, and numbers accurate.\\n"
            "Improve readability and flow.\\n"
            f"Must preserve these keywords if present: {keywords_line}.\\n"
            "Return only final rewritten text, no explanation.\\n\\n"
            f"Original text:\\n{text}"
        )

    @staticmethod
    def _fallback_rewrite(text: str, style: str, variant_idx: int) -> str:
        cleaned = " ".join(text.split())
        if style == "concise":
            short = cleaned[: min(len(cleaned), 500)]
            return short if variant_idx == 1 else f"Tóm tắt nhanh: {short}"
        if style == "engaging":
            return f"✨ {cleaned}" if variant_idx == 1 else f"🔥 {cleaned}"
        if style == "formal":
            return cleaned.replace("!", ".")
        if style == "seo":
            base = cleaned
            suffix = "#keyword #content" if variant_idx == 1 else "#seo #youtube #ai"
            return f"{base}\\n\\n{suffix}"
        return cleaned if variant_idx == 1 else f"{cleaned}"

    def _variant_styles(self, requested_style: RewriteStyle, variant_count: int) -> List[RewriteStyle]:
        style_pool: List[RewriteStyle] = [requested_style, "concise", "engaging", "formal", "seo", "natural"]
        result: List[RewriteStyle] = []
        for s in style_pool:
            if s not in result:
                result.append(s)
            if len(result) >= variant_count:
                break
        return result

    async def _call_gemini(self, prompt: str, temperature: float = 0.6) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "topP": 0.9},
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        return (data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip())

    async def rewrite(
        self,
        text: str,
        style: RewriteStyle,
        language: str,
        preserve_keywords: List[str],
        variant_count: int,
    ) -> tuple[List[dict], str, bool]:
        styles = self._variant_styles(style, variant_count)
        variants: List[dict] = []
        fallback_used = False

        for idx, chosen_style in enumerate(styles, start=1):
            prompt = self._build_prompt(text, chosen_style, language, preserve_keywords, idx)

            if self.api_key:
                try:
                    out = await self._call_gemini(prompt=prompt, temperature=0.45 + (idx * 0.1))
                    if not out:
                        raise ValueError("Gemini returned empty output")
                except Exception:
                    out = self._fallback_rewrite(text, chosen_style, idx)
                    fallback_used = True
            else:
                out = self._fallback_rewrite(text, chosen_style, idx)
                fallback_used = True

            variants.append({"index": idx, "style": chosen_style, "text": out})

        model_used = self.model if self.api_key and not fallback_used else "fallback-local"
        return variants, model_used, fallback_used
