from dataclasses import dataclass
import logging
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
        logger: logging.Logger | None = None,
    ):
        self.config = config
        self.repository = repository
        self.parser_factory = parser_factory
        self.serialization_service = serialization_service
        self.chunking_service = chunking_service
        self.clock = clock
        self.logger = logger or logging.getLogger(__name__)

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
        self._log_event("document.uploaded", document=document)
        conversion_duration_ms = 0
        serialization_duration_ms = 0
        chunking_duration_ms = 0

        try:
            self._ensure_not_timed_out(started_at)
            self.repository.update_document_status(document.id, DocumentStatus.CONVERTING)
            self._log_event("document.conversion.started", document=document)
            conversion_started_at = self.clock()
            parser = self.parser_factory.get(document.extension)
            parsed = parser.parse(stored_upload.original_path)
            conversion_duration_ms = duration_ms(conversion_started_at, self.clock())

            self._ensure_not_timed_out(started_at)
            self._log_event(
                "document.conversion.completed",
                document=document,
                parsed=parsed,
                duration_ms=conversion_duration_ms,
            )
            if parsed.metadata.get("ocr_used") is True:
                self._log_event("document.ocr.used", document=document, parsed=parsed)

            self.repository.update_document_status(document.id, DocumentStatus.NORMALIZING)
            self._log_event("document.serialization.started", document=document, parsed=parsed)
            serialization_started_at = self.clock()
            serialized = self.serialization_service.serialize(parsed, stored_upload.document_dir)
            serialization_duration_ms = duration_ms(serialization_started_at, self.clock())

            self._ensure_not_timed_out(started_at)
            self._log_event(
                "document.serialization.completed",
                document=document,
                parsed=parsed,
                duration_ms=serialization_duration_ms,
            )
            self.repository.update_document_status(document.id, DocumentStatus.CHUNKING)
            self._log_event("document.chunking.started", document=document, parsed=parsed)
            chunking_started_at = self.clock()
            chunks = self.chunking_service.chunk(
                parsed,
                document_id=document.id,
                document_dir=stored_upload.document_dir,
                filename=document.filename,
                chunker=chunker,
                max_tokens=max_tokens,
            )
            chunking_duration_ms = duration_ms(chunking_started_at, self.clock())

            self._ensure_not_timed_out(started_at)
            self._log_event(
                "document.chunking.completed",
                document=document,
                parsed=parsed,
                duration_ms=chunking_duration_ms,
                chunk_count=len(chunks),
            )
            self.repository.save_chunks(document.id, chunks)

            self._ensure_not_timed_out(started_at)
            total_duration_ms = duration_ms(started_at, self.clock())
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
                    "conversion_duration_ms": conversion_duration_ms,
                    "serialization_duration_ms": serialization_duration_ms,
                    "chunking_duration_ms": chunking_duration_ms,
                    "total_duration_ms": total_duration_ms,
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
            self._log_event(
                "document.processing.failed",
                document=document,
                error_code=error.code.value,
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
            self._log_event(
                "document.processing.failed",
                document=document,
                error_code=app_error.code.value,
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

    def _log_event(
        self,
        event: str,
        *,
        document: DocumentRecord,
        parsed=None,
        duration_ms: int | None = None,
        chunk_count: int | None = None,
        error_code: str | None = None,
    ) -> None:
        fields = {
            "event": event,
            "document_id": document.id,
            "filename": document.filename,
            "content_type": document.content_type,
        }
        if parsed is not None:
            fields.update(
                {
                    "source_format": parsed.source_format,
                    "page_count": parsed.metadata.get("page_count"),
                    "ocr_used": parsed.metadata.get("ocr_used"),
                    "table_count": parsed.metadata.get("table_count"),
                }
            )
        if duration_ms is not None:
            fields["duration_ms"] = duration_ms
        if chunk_count is not None:
            fields["chunk_count"] = chunk_count
        if error_code is not None:
            fields["error_code"] = error_code

        self.logger.info(
            event,
            extra={
                "event": event,
                "structured_fields": fields,
            },
        )


def duration_ms(started_at: float, ended_at: float) -> int:
    return max(0, int((ended_at - started_at) * 1000))
