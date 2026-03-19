from typing import List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


RewriteStyle = Literal["natural", "concise", "engaging", "formal", "seo"]


class RewriteRequest(BaseModel):
    text: str = Field(min_length=1, description="Original text to rewrite")
    style: RewriteStyle = "natural"
    language: str = Field(default="vi", description="Target language, e.g. vi or en")
    preserve_keywords: List[str] = Field(default_factory=list)


class RewriteResponse(BaseModel):
    rewritten_text: str
    model_used: str
    fallback_used: bool = False


class YouTubeExtractRequest(BaseModel):
    url: HttpUrl
    include_transcript: bool = True
    language_priority: List[str] = Field(default_factory=lambda: ["vi", "en"])


class YouTubeExtractResponse(BaseModel):
    source_url: str
    video_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    uploader: Optional[str] = None
    channel: Optional[str] = None
    duration_seconds: Optional[int] = None
    upload_date: Optional[str] = None
    transcript: Optional[str] = None
    transcript_language: Optional[str] = None
    transcript_source: Optional[str] = None
    chapters: List[dict] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
