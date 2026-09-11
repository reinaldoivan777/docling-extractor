from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.app.parsers.docling_parser import DoclingParser
from backend.app.utils.errors import AppError, ErrorCode


class FakeDoclingDocument:
    def __init__(
        self,
        *,
        markdown: str = "Document content",
        text: str = "Document content",
        pages=None,
        tables=None,
        pictures=None,
        metadata=None,
    ):
        self._markdown = markdown
        self._text = text
        self.pages = pages
        self.tables = tables
        self.pictures = pictures
        self.metadata = metadata or {}

    def export_to_markdown(self):
        return self._markdown

    def export_to_text(self):
        return self._text


class FakeDoclingService:
    def __init__(self, document=None, *, error: Exception | None = None):
        self.document = document or FakeDoclingDocument()
        self.error = error
        self.convert_calls = []
        self.ensure_xls_support_calls = 0

    def convert(self, file_path):
        self.convert_calls.append(Path(file_path))
        if self.error:
            raise self.error
        return self.document

    def ensure_xls_support(self):
        self.ensure_xls_support_calls += 1


class FailingXlsService(FakeDoclingService):
    def ensure_xls_support(self):
        self.ensure_xls_support_calls += 1
        raise AppError(
            code=ErrorCode.XLS_RUNTIME_UNAVAILABLE,
            message="Legacy XLS support requires LibreOffice runtime.",
        )


class DoclingParserTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_file(self, filename: str) -> Path:
        path = self.root / filename
        path.write_bytes(b"fixture")
        return path

    def test_parse_returns_parsed_document_with_docling_document(self):
        document = FakeDoclingDocument(
            markdown="# Heading\n\nBody",
            text="Heading\n\nBody",
            pages={1: object(), 2: object()},
            tables=[object()],
            pictures=[],
            metadata={"ocr_used": True},
        )
        service = FakeDoclingService(document)
        parser = DoclingParser(service)
        path = self.make_file("sample.pdf")

        parsed = parser.parse(path)

        self.assertIs(parsed.structured_document, document)
        self.assertEqual(parsed.source_format, "pdf")
        self.assertEqual(parsed.markdown, "# Heading\n\nBody")
        self.assertEqual(parsed.text, "Heading\n\nBody")
        self.assertEqual(parsed.metadata["source_format"], "pdf")
        self.assertEqual(parsed.metadata["page_count"], 2)
        self.assertEqual(parsed.metadata["table_count"], 1)
        self.assertEqual(parsed.metadata["picture_count"], 0)
        self.assertTrue(parsed.metadata["ocr_used"])
        self.assertEqual(service.convert_calls, [path])

    def test_parse_xls_checks_runtime_support_before_conversion(self):
        service = FakeDoclingService()
        parser = DoclingParser(service)

        parser.parse(self.make_file("legacy.xls"))

        self.assertEqual(service.ensure_xls_support_calls, 1)
        self.assertEqual(len(service.convert_calls), 1)

    def test_missing_xls_runtime_error_is_preserved(self):
        service = FailingXlsService()
        parser = DoclingParser(service)

        with self.assertRaises(AppError) as context:
            parser.parse(self.make_file("legacy.xls"))

        self.assertEqual(context.exception.code, ErrorCode.XLS_RUNTIME_UNAVAILABLE)
        self.assertEqual(service.convert_calls, [])

    def test_conversion_failure_maps_to_document_conversion_failed(self):
        service = FakeDoclingService(error=RuntimeError("boom"))
        parser = DoclingParser(service)

        with self.assertRaises(AppError) as context:
            parser.parse(self.make_file("sample.pdf"))

        self.assertEqual(context.exception.code, ErrorCode.DOCUMENT_CONVERSION_FAILED)
        self.assertEqual(context.exception.message, "Unable to convert document with Docling.")

    def test_docling_app_error_is_preserved(self):
        service = FakeDoclingService(
            error=AppError(
                code=ErrorCode.DOCLING_INITIALIZATION_FAILED,
                message="Docling unavailable.",
            )
        )
        parser = DoclingParser(service)

        with self.assertRaises(AppError) as context:
            parser.parse(self.make_file("sample.pdf"))

        self.assertEqual(context.exception.code, ErrorCode.DOCLING_INITIALIZATION_FAILED)

    def test_empty_extraction_returns_empty_extraction_error(self):
        service = FakeDoclingService(
            FakeDoclingDocument(markdown="", text="", pages=[], tables=[], pictures=[])
        )
        parser = DoclingParser(service)

        with self.assertRaises(AppError) as context:
            parser.parse(self.make_file("empty.pdf"))

        self.assertEqual(context.exception.code, ErrorCode.EMPTY_EXTRACTION)

    def test_parser_without_service_returns_initialization_error(self):
        parser = DoclingParser()

        with self.assertRaises(AppError) as context:
            parser.parse(self.make_file("sample.pdf"))

        self.assertEqual(context.exception.code, ErrorCode.DOCLING_INITIALIZATION_FAILED)


if __name__ == "__main__":
    unittest.main()
