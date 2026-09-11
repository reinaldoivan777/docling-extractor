from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChunkRecord:
    id: str
    document_id: str
    chunk_index: int
    content: str
    contextualized_content: str
    token_count: int | None = None
    metadata: dict = field(default_factory=dict)
    created_at: str | None = None
