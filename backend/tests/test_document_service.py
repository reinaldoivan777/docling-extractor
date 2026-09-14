from io import BytesIO
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from werkzeug.datastructures import FileStorage, MultiDict

from backend.app.config import AppConfig
from backend.app.models.document import DocumentStatus
from backend.app.models.parsed_document import ParsedDocument
from backend.app.parsers.text_parser import TextParser
from backend.app.repositories.document_repository import DocumentRepository
from backend.app.services.chunking_service import ChunkingService
from backend.app.services.document_service import DocumentService
from backend.app.services.serialization_service import SerializationService
from backend.app.utils.errors import AppError, ErrorCode


def make_config(root: Path, *, timeout_seconds: int = 120) -> AppConfig:
    return AppConfig(
        flask_env="test",
        allowed_extensions={".pdf", ".docx", ".txt", ".md", ".xlsx", ".xls", ".csv"},
        max_upload_size_mb=20,
        max_document_pages=200,
        document_processing_timeout_seconds=timeout_seconds,
        docling_ocr_enabled=True,
        docling_force_ocr=False,
        docling_table_structure_enabled=True,
        docling_table_mode="accurate",
        default_chunker="hybrid",
        default_chunk_max_tokens=3,
        default_chunk_tokenizer="sentence-transformers/all-MiniLM-L6-v2",
        enable_legacy_xls=True,
        storage_path=root / "documents",
        database_url=f"sqlite:///{root / 'app.db'}",
    )


def upload_files(
    filename: str = "note.txt",
    content: bytes = b"one two three four",
    content_type: str = "text/plain",
) -> MultiDict:
    return MultiDict(
        {
            "file": FileStorage(
                stream=BytesIO(content),
                filename=filename,
                content_type=content_type,
            )
        }
    )


class FakeParserFactory:
    def __init__(self, parser):
        self.parser = parser
        self.extensions = []

    def get(self, extension):
        self.extensions.append(extension)
        return self.parser


class FailingParser:
    def parse(self, file_path):
        raise AppError(
            code=ErrorCode.DOCUMENT_CONVERSION_FAILED,
            message="Parser failed.",
        )


class SlowParser:
    def parse(self, file_path):
        return ParsedDocument(
            source_format="txt",
            structured_document={"type": "text", "content": "hello"},
            text="hello",
            markdown="hello",
            metadata={"source_format": "txt"},
        )


class MetadataParser:
    def parse(self, file_path):
        return ParsedDocument(
            source_format="pdf",
            structured_document={"type": "text", "content": "secret body text with citations"},
            text="secret body text with citations",
            markdown="secret body text with citations",
            metadata={
                "source_format": "pdf",
                "page_count": 7,
                "table_count": 2,
                "ocr_used": True,
            },
        )


class SequenceClock:
    def __init__(self, values):
        self.values = list(values)
        self.last = self.values[-1]

    def __call__(self):
        if self.values:
            self.last = self.values.pop(0)
        return self.last


class ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class DocumentServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.config = make_config(self.root)
        self.repository = DocumentRepository(
            database_path=self.root / "app.db",
            storage_path=self.config.storage_path,
        )
        self.repository.init_db()

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_service(self, parser, *, clock=None, config=None, logger=None):
        active_config = config or self.config
        return DocumentService(
            config=active_config,
            repository=self.repository,
            parser_factory=FakeParserFactory(parser),
            serialization_service=SerializationService(),
            chunking_service=ChunkingService(active_config),
            clock=clock or (lambda: 0),
            logger=logger,
        )

    def test_successful_upload_reaches_completed_and_persists_artifacts_and_chunks(self):
        service = self.make_service(TextParser())

        result = service.process_upload(upload_files(), max_tokens=3)
        document = self.repository.get_document(result.document.id)
        chunks = self.repository.list_chunks(result.document.id)

        self.assertEqual(document.status, DocumentStatus.COMPLETED)
        self.assertEqual(document.chunk_count, 2)
        self.assertEqual(result.chunk_count, 2)
        self.assertEqual(len(chunks), 2)
        self.assertTrue((self.config.storage_path / document.id / "document.md").exists())
        self.assertTrue((self.config.storage_path / document.id / "document.txt").exists())
        self.assertTrue((self.config.storage_path / document.id / "document.json").exists())
        self.assertTrue((self.config.storage_path / document.id / "chunks.json").exists())
        self.assertEqual(document.metadata["metrics"]["chunk_count"], 2)
        self.assertEqual(document.metadata["chunking"]["max_tokens"], 3)
        self.assertIn("conversion_duration_ms", document.metadata["metrics"])
        self.assertIn("serialization_duration_ms", document.metadata["metrics"])
        self.assertIn("chunking_duration_ms", document.metadata["metrics"])

    def test_failure_marks_document_failed_and_persists_error(self):
        service = self.make_service(FailingParser())

        with self.assertRaises(AppError):
            service.process_upload(upload_files())

        stored_documents = list((self.config.storage_path).iterdir())
        self.assertEqual(len(stored_documents), 1)
        document_id = stored_documents[0].name
        document = self.repository.get_document(document_id)

        self.assertEqual(document.status, DocumentStatus.FAILED)
        self.assertEqual(document.error_code, ErrorCode.DOCUMENT_CONVERSION_FAILED.value)
        self.assertEqual(document.error_message, "Parser failed.")

    def test_timeout_marks_document_failed(self):
        config = make_config(self.root, timeout_seconds=1)
        self.config = config
        self.repository.storage_path = config.storage_path
        service = self.make_service(SlowParser(), clock=SequenceClock([0, 2]), config=config)

        with self.assertRaises(AppError) as context:
            service.process_upload(upload_files())

        document_id = next(config.storage_path.iterdir()).name
        document = self.repository.get_document(document_id)

        self.assertEqual(context.exception.code, ErrorCode.PROCESSING_TIMEOUT)
        self.assertEqual(document.status, DocumentStatus.FAILED)
        self.assertEqual(document.error_code, ErrorCode.PROCESSING_TIMEOUT.value)

    def test_logs_lifecycle_events_and_persists_stage_durations_without_document_content(self):
        logger = logging.getLogger("document-service-test")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        handler = ListHandler()
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)
        clock = SequenceClock([0, 0, 1, 1.25, 1.25, 1.3, 1.45, 1.45, 1.5, 1.75, 1.75, 1.75, 2.0])
        service = self.make_service(MetadataParser(), clock=clock, logger=logger)

        result = service.process_upload(
            upload_files(filename="report.pdf", content_type="application/pdf"),
            max_tokens=3,
        )
        document = self.repository.get_document(result.document.id)
        events = [record.event for record in handler.records]

        self.assertEqual(
            events,
            [
                "document.uploaded",
                "document.conversion.started",
                "document.conversion.completed",
                "document.ocr.used",
                "document.serialization.started",
                "document.serialization.completed",
                "document.chunking.started",
                "document.chunking.completed",
            ],
        )
        completed = handler.records[2].structured_fields
        self.assertEqual(completed["document_id"], document.id)
        self.assertEqual(completed["filename"], "report.pdf")
        self.assertEqual(completed["content_type"], "application/pdf")
        self.assertEqual(completed["source_format"], "pdf")
        self.assertEqual(completed["page_count"], 7)
        self.assertTrue(completed["ocr_used"])
        self.assertEqual(completed["table_count"], 2)
        self.assertEqual(completed["duration_ms"], 250)
        self.assertEqual(handler.records[-1].structured_fields["chunk_count"], 2)
        self.assertEqual(document.metadata["metrics"]["conversion_duration_ms"], 250)
        self.assertEqual(document.metadata["metrics"]["serialization_duration_ms"], 149)
        self.assertEqual(document.metadata["metrics"]["chunking_duration_ms"], 250)
        self.assertEqual(document.metadata["metrics"]["total_duration_ms"], 2000)

        logged_payload = " ".join(
            f"{record.getMessage()} {getattr(record, 'structured_fields', {})}"
            for record in handler.records
        )
        self.assertNotIn("secret body text with citations", logged_payload)

    def test_processing_failure_logs_stable_error_code_without_content(self):
        logger = logging.getLogger("document-service-failure-test")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        handler = ListHandler()
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)
        service = self.make_service(FailingParser(), logger=logger)

        with self.assertRaises(AppError):
            service.process_upload(upload_files(content=b"do not log this body"))

        failure = handler.records[-1]
        self.assertEqual(failure.event, "document.processing.failed")
        self.assertEqual(
            failure.structured_fields["error_code"],
            ErrorCode.DOCUMENT_CONVERSION_FAILED.value,
        )
        self.assertNotIn("do not log this body", str(failure.structured_fields))


if __name__ == "__main__":
    unittest.main()
