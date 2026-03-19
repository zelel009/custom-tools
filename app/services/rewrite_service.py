from __future__ import annotations

from typing import List

import httpx

from app.core.config import settings


class RewriteService:
    def __init__(self) -> None:
        self.api_key = settings.gemini_api_key.strip()
        self.model = settings.gemini_model
        self.timeout = settings.http_timeout_seconds

    def _build_prompt(self, text: str, style: str, language: str, preserve_keywords: List[str]) -> str:
        keywords_line = ", ".join(preserve_keywords) if preserve_keywords else "(none)"
        return (
            f"Rewrite the following content in {language}.\\n"
            f"Style: {style}.\\n"
            "Keep original meaning, facts, names, and numbers accurate.\\n"
            "Improve readability and flow.\\n"
            f"Must preserve these keywords if present: {keywords_line}.\\n"
            "Return only final rewritten text, no explanation.\\n\\n"
            f"Original text:\\n{text}"
        )

    def _fallback_rewrite(self, text: str, style: str) -> str:
        cleaned = " ".join(text.split())
        if style == "concise":
            return cleaned[: min(len(cleaned), 500)]
        if style == "engaging":
            return f"✨ {cleaned}"
        if style == "formal":
            return cleaned.replace("!", ".")
        if style == "seo":
            return f"{cleaned}\n\n#keyword #content"
        return cleaned

    async def rewrite(self, text: str, style: str, language: str, preserve_keywords: List[str]) -> tuple[str, str, bool]:
        prompt = self._build_prompt(text, style, language, preserve_keywords)

        if not self.api_key:
            return self._fallback_rewrite(text, style), "fallback-local", True

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ]
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        try:
            text_out = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            if not text_out:
                raise ValueError("Gemini returned empty text")
            return text_out, self.model, False
        except Exception:
            return self._fallback_rewrite(text, style), "fallback-local", True
