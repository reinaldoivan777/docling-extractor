from dataclasses import asdict
from pathlib import Path
from typing import Any
import json
import uuid

from docling_core.transforms.chunker.tokenizer.base import BaseTokenizer

from ..config import AppConfig
from ..models.chunk import ChunkRecord
from ..models.parsed_document import ParsedDocument
from ..utils.errors import AppError, ErrorCode


class WhitespaceTokenizer(BaseTokenizer):
    max_tokens: int = 512

    def count_tokens(self, text: str) -> int:
        return count_tokens(text)

    def get_max_tokens(self) -> int:
        return self.max_tokens

    def get_tokenizer(self):
        return self


class ChunkingService:
    def __init__(
        self,
        config: AppConfig,
        *,
        hybrid_chunker_cls: type | None = None,
        hierarchical_chunker_cls: type | None = None,
    ):
        self.config = config
        self.hybrid_chunker_cls = hybrid_chunker_cls
        self.hierarchical_chunker_cls = hierarchical_chunker_cls

    def chunk(
        self,
        parsed_document: ParsedDocument,
        *,
        document_id: str,
        document_dir: str | Path,
        filename: str | None = None,
        chunker: str | None = None,
        max_tokens: int | None = None,
    ) -> list[ChunkRecord]:
        selected_chunker = (chunker or self.config.default_chunker).lower()
        token_limit = max_tokens or self.config.default_chunk_max_tokens
        output_dir = Path(document_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            validate_chunk_config(selected_chunker, token_limit)

            if is_lightweight_text_document(parsed_document):
                chunks = self._chunk_text(
                    parsed_document,
                    document_id=document_id,
                    filename=filename,
                    max_tokens=token_limit,
                )
            else:
                chunks = self._chunk_docling_document(
                    parsed_document,
                    document_id=document_id,
                    filename=filename,
                    chunker=selected_chunker,
                    max_tokens=token_limit,
                )

            write_chunks_json(chunks, output_dir / "chunks.json")
            return chunks
        except AppError:
            raise
        except Exception as error:
            raise AppError(
                code=ErrorCode.CHUNKING_FAILED,
                message="Unable to chunk parsed document.",
            ) from error

    def _chunk_docling_document(
        self,
        parsed_document: ParsedDocument,
        *,
        document_id: str,
        filename: str | None,
        chunker: str,
        max_tokens: int,
    ) -> list[ChunkRecord]:
        docling_chunker = self._build_docling_chunker(chunker, max_tokens)
        doc_chunks = list(docling_chunker.chunk(dl_doc=parsed_document.structured_document))
        records: list[ChunkRecord] = []

        for index, doc_chunk in enumerate(doc_chunks):
            content = extract_chunk_text(doc_chunk)
            contextualized_content = contextualize_chunk(docling_chunker, doc_chunk, content)
            metadata = extract_chunk_metadata(
                doc_chunk,
                filename=filename,
                source_format=parsed_document.source_format,
            )
            records.append(
                ChunkRecord(
                    id=f"chunk_{uuid.uuid4().hex}",
                    document_id=document_id,
                    chunk_index=index,
                    content=content,
                    contextualized_content=contextualized_content,
                    token_count=count_tokens(contextualized_content),
                    metadata=metadata,
                )
            )

        if not records:
            raise AppError(
                code=ErrorCode.CHUNKING_FAILED,
                message="Document content did not produce any chunks.",
            )

        return records

    def _chunk_text(
        self,
        parsed_document: ParsedDocument,
        *,
        document_id: str,
        filename: str | None,
        max_tokens: int,
    ) -> list[ChunkRecord]:
        text = parsed_document.text or parsed_document.markdown
        words = text.split()
        if not words:
            raise AppError(
                code=ErrorCode.CHUNKING_FAILED,
                message="Text content did not produce any chunks.",
            )

        records: list[ChunkRecord] = []
        for index, start in enumerate(range(0, len(words), max_tokens)):
            content = " ".join(words[start : start + max_tokens])
            metadata = default_metadata(filename=filename, source_format=parsed_document.source_format)
            records.append(
                ChunkRecord(
                    id=f"chunk_{uuid.uuid4().hex}",
                    document_id=document_id,
                    chunk_index=index,
                    content=content,
                    contextualized_content=content,
                    token_count=count_tokens(content),
                    metadata=metadata,
                )
            )

        return records

    def _build_docling_chunker(self, chunker: str, max_tokens: int):
        if chunker == "hybrid":
            chunker_cls = self.hybrid_chunker_cls
            if chunker_cls is None:
                from docling.chunking import HybridChunker

                chunker_cls = HybridChunker

            return chunker_cls(tokenizer=WhitespaceTokenizer(max_tokens=max_tokens))

        if chunker == "hierarchical":
            chunker_cls = self.hierarchical_chunker_cls
            if chunker_cls is None:
                from docling.chunking import HierarchicalChunker

                chunker_cls = HierarchicalChunker

            return chunker_cls()

        raise AppError(
            code=ErrorCode.CHUNKING_FAILED,
            message=f"Unsupported chunker: {chunker}.",
        )


def is_lightweight_text_document(parsed_document: ParsedDocument) -> bool:
    structured = parsed_document.structured_document
    return isinstance(structured, dict) and structured.get("type") == "text"


def validate_chunk_config(chunker: str, max_tokens: int) -> None:
    if chunker not in {"hybrid", "hierarchical"}:
        raise AppError(
            code=ErrorCode.CHUNKING_FAILED,
            message=f"Unsupported chunker: {chunker}.",
        )

    if max_tokens < 1:
        raise AppError(
            code=ErrorCode.CHUNKING_FAILED,
            message="Chunk max_tokens must be greater than zero.",
        )


def count_tokens(text: str) -> int:
    return len(text.split())


def extract_chunk_text(doc_chunk: Any) -> str:
    text = getattr(doc_chunk, "text", "")
    return text if isinstance(text, str) else str(text)


def contextualize_chunk(chunker: Any, doc_chunk: Any, fallback_content: str) -> str:
    contextualize = getattr(chunker, "contextualize", None)
    if not callable(contextualize):
        return fallback_content

    contextualized = contextualize(doc_chunk)
    return contextualized if isinstance(contextualized, str) else str(contextualized)


def extract_chunk_metadata(doc_chunk: Any, *, filename: str | None, source_format: str) -> dict:
    metadata = default_metadata(filename=filename, source_format=source_format)
    meta = getattr(doc_chunk, "meta", None)
    if meta is None:
        return metadata

    headings = getattr(meta, "headings", None)
    captions = getattr(meta, "captions", None)
    doc_items = getattr(meta, "doc_items", None) or []

    metadata["headings"] = list(headings or [])
    metadata["captions"] = list(captions or [])
    metadata["source_items"] = [source_item_ref(item) for item in doc_items]
    metadata["page_numbers"] = sorted(page_numbers_from_items(doc_items))
    metadata["table_refs"] = [ref for item in doc_items if (ref := table_ref(item)) is not None]

    return metadata


def default_metadata(*, filename: str | None, source_format: str) -> dict:
    return {
        "filename": filename,
        "source_format": source_format,
        "headings": [],
        "page_numbers": [],
        "captions": [],
        "table_refs": [],
        "source_items": [],
    }


def source_item_ref(item: Any) -> str:
    for attribute in ("self_ref", "cref", "id"):
        value = getattr(item, attribute, None)
        if value:
            return str(value)

    return repr(item)


def table_ref(item: Any) -> str | None:
    label = getattr(item, "label", None)
    if label is not None and "table" in str(label).lower():
        return source_item_ref(item)

    name = type(item).__name__.lower()
    if "table" in name:
        return source_item_ref(item)

    return None


def page_numbers_from_items(doc_items: list[Any]) -> set[int]:
    page_numbers: set[int] = set()
    for item in doc_items:
        prov_items = getattr(item, "prov", None) or []
        for prov in prov_items:
            page_no = getattr(prov, "page_no", None)
            if isinstance(page_no, int):
                page_numbers.add(page_no)

    return page_numbers


def write_chunks_json(chunks: list[ChunkRecord], path: Path) -> None:
    payload = [
        {
            **asdict(chunk),
            "index": chunk.chunk_index,
        }
        for chunk in chunks
    ]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
