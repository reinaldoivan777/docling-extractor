from dataclasses import dataclass, field
from enum import StrEnum


class DocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    CONVERTING = "CONVERTING"
    NORMALIZING = "NORMALIZING"
    CHUNKING = "CHUNKING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class DocumentRecord:
    id: str
    filename: str
    content_type: str
    extension: str
    size: int
    status: DocumentStatus
    page_count: int | None = None
    table_count: int | None = None
    picture_count: int | None = None
    markdown_character_count: int | None = None
    chunk_count: int = 0
    ocr_used: bool | None = None
    metadata: dict = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
