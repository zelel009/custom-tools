from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


RewriteStyle = Literal["natural", "concise", "engaging", "formal", "seo"]
ExportFormat = Literal["txt", "json", "srt"]


class RewriteRequest(BaseModel):
    text: str = Field(min_length=1, description="Original text to rewrite")
    style: RewriteStyle = "natural"
    language: str = Field(default="vi", description="Target language, e.g. vi or en")
    preserve_keywords: List[str] = Field(default_factory=list)
    variant_count: int = Field(default=1, ge=1, le=3)


class RewriteVariant(BaseModel):
    index: int
    style: RewriteStyle
    text: str
    word_count: int
    char_count: int
    preserved_keywords: List[str] = Field(default_factory=list)


class RewriteComparison(BaseModel):
    original_word_count: int
    original_char_count: int
    variants_summary: List[dict[str, Any]] = Field(default_factory=list)


class RewriteResponse(BaseModel):
    model_used: str
    fallback_used: bool = False
    variants: List[RewriteVariant]
    comparison: RewriteComparison


class YouTubeExtractRequest(BaseModel):
    url: HttpUrl
    include_transcript: bool = True
    language_priority: List[str] = Field(default_factory=lambda: ["vi", "en"])
    max_items: int = Field(default=10, ge=1, le=50)
    export_formats: List[ExportFormat] = Field(default_factory=lambda: ["json"])


class YouTubeVideoItem(BaseModel):
    source_url: Optional[str] = None
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


class YouTubeExtractResponse(BaseModel):
    kind: Literal["video", "playlist"]
    source_url: str
    item_count: int
    items: List[YouTubeVideoItem] = Field(default_factory=list)
    export_files: dict[str, str] = Field(default_factory=dict)


class YouTubeJobCreateResponse(BaseModel):
    job_id: str
    status: str


class YouTubeJobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[YouTubeExtractResponse] = None
    error: Optional[str] = None
    export_files: dict[str, str] = Field(default_factory=dict)
    created_at: str
    updated_at: str
