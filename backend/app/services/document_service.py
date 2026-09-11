from dataclasses import dataclass
from time import monotonic
from typing import Callable

from werkzeug.datastructures import FileStorage, MultiDict

from ..config import AppConfig
from ..models.document import DocumentRecord, DocumentStatus
from ..parsers.factory import ParserFactory
from ..repositories.document_repository import DocumentRepository
from ..utils.errors import AppError, ErrorCode
from ..utils.file import save_validated_upload
from .chunking_service import ChunkingService
from .serialization_service import SerializationService


@dataclass(frozen=True)
class ProcessingResult:
    document: DocumentRecord
    chunk_count: int


class DocumentService:
    def __init__(
        self,
        *,
        config: AppConfig,
        repository: DocumentRepository,
        parser_factory: ParserFactory,
        serialization_service: SerializationService,
        chunking_service: ChunkingService,
        clock: Callable[[], float] = monotonic,
    ):
        self.config = config
        self.repository = repository
        self.parser_factory = parser_factory
        self.serialization_service = serialization_service
        self.chunking_service = chunking_service
        self.clock = clock

    def process_upload(
        self,
        files: MultiDict[str, FileStorage],
        *,
        chunker: str | None = None,
        max_tokens: int | None = None,
    ) -> ProcessingResult:
        started_at = self.clock()
        stored_upload = save_validated_upload(files, self.config)
        document = self.repository.create_document(
            document_id=stored_upload.document_id,
            filename=stored_upload.display_filename,
            content_type=stored_upload.content_type,
            extension=stored_upload.extension,
            size=stored_upload.size,
            metadata={
                "original_path": str(stored_upload.original_path),
            },
        )

        try:
            self._ensure_not_timed_out(started_at)
            self.repository.update_document_status(document.id, DocumentStatus.CONVERTING)
            parser = self.parser_factory.get(document.extension)
            parsed = parser.parse(stored_upload.original_path)

            self._ensure_not_timed_out(started_at)
            self.repository.update_document_status(document.id, DocumentStatus.NORMALIZING)
            serialized = self.serialization_service.serialize(parsed, stored_upload.document_dir)

            self._ensure_not_timed_out(started_at)
            self.repository.update_document_status(document.id, DocumentStatus.CHUNKING)
            chunks = self.chunking_service.chunk(
                parsed,
                document_id=document.id,
                document_dir=stored_upload.document_dir,
                filename=document.filename,
                chunker=chunker,
                max_tokens=max_tokens,
            )
            self.repository.save_chunks(document.id, chunks)

            self._ensure_not_timed_out(started_at)
            metadata = {
                **document.metadata,
                **parsed.metadata,
                "artifacts": {
                    "document_json_path": str(serialized.json_path),
                    "document_markdown_path": str(serialized.markdown_path),
                    "document_text_path": str(serialized.text_path),
                    "chunks_json_path": str(stored_upload.document_dir / "chunks.json"),
                },
                "metrics": {
                    "upload_size_bytes": document.size,
                    "markdown_character_count": len(serialized.markdown),
                    "chunk_count": len(chunks),
                    "total_duration_ms": int((self.clock() - started_at) * 1000),
                },
                "chunking": {
                    "chunker": chunker or self.config.default_chunker,
                    "max_tokens": max_tokens or self.config.default_chunk_max_tokens,
                },
            }
            self.repository.save_processing_result(
                document.id,
                page_count=parsed.metadata.get("page_count"),
                table_count=parsed.metadata.get("table_count"),
                picture_count=parsed.metadata.get("picture_count"),
                markdown_character_count=len(serialized.markdown),
                chunk_count=len(chunks),
                ocr_used=parsed.metadata.get("ocr_used"),
                metadata=metadata,
            )
        except AppError as error:
            self.repository.update_document_status(
                document.id,
                DocumentStatus.FAILED,
                error_code=error.code.value,
                error_message=error.message,
            )
            raise
        except Exception as error:
            app_error = AppError(
                code=ErrorCode.DOCUMENT_CONVERSION_FAILED,
                message="Document processing failed.",
            )
            self.repository.update_document_status(
                document.id,
                DocumentStatus.FAILED,
                error_code=app_error.code.value,
                error_message=app_error.message,
            )
            raise app_error from error

        completed = self.repository.get_document(document.id)
        if completed is None:
            raise AppError(
                code=ErrorCode.DOCUMENT_NOT_FOUND,
                message="Processed document was not found.",
            )

        return ProcessingResult(document=completed, chunk_count=len(chunks))

    def _ensure_not_timed_out(self, started_at: float) -> None:
        elapsed = self.clock() - started_at
        if elapsed > self.config.document_processing_timeout_seconds:
            raise AppError(
                code=ErrorCode.PROCESSING_TIMEOUT,
                message="Document processing timed out.",
            )
