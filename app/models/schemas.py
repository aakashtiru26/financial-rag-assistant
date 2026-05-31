from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str


class DocumentRecord(BaseModel):
    document_id: str
    filename: str
    content_type: str | None = None
    file_path: str
    file_sha256: str
    uploaded_at: datetime
    chunk_count: int = 0


class UploadResponse(BaseModel):
    document: DocumentRecord
    message: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentRecord]


class DeleteResponse(BaseModel):
    document_id: str
    deleted: bool
    message: str


class ReindexResponse(BaseModel):
    indexed_documents: int
    indexed_chunks: int
    message: str


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=20)


class SourceChunk(BaseModel):
    document_id: str
    filename: str
    chunk_id: str
    page: int | None = None
    row: int | None = None
    score: float | None = None
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    answer: str
    citations: list[str]
    sources: list[SourceChunk]
