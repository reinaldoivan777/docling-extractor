from pathlib import Path
import unittest

from backend.app.config import AppConfig
from backend.app.models.parsed_document import ParsedDocument
from backend.app.parsers.base import DocumentParser
from backend.app.parsers.factory import ParserFactory
from backend.app.utils.errors import UnsupportedFileTypeError


class DummyDoclingParser(DocumentParser):
    def parse(self, file_path: str | Path) -> ParsedDocument:
        return ParsedDocument(source_format="docling", structured_document={})


class DummyTextParser(DocumentParser):
    def parse(self, file_path: str | Path) -> ParsedDocument:
        return ParsedDocument(source_format="txt", structured_document={})


def make_config(*, enable_legacy_xls: bool = True) -> AppConfig:
    return AppConfig(
        flask_env="test",
        allowed_extensions={".pdf", ".docx", ".txt", ".md", ".xlsx", ".xls", ".csv"},
        max_upload_size_mb=20,
        max_document_pages=200,
        document_processing_timeout_seconds=120,
        docling_ocr_enabled=True,
        docling_force_ocr=False,
        docling_table_structure_enabled=True,
        docling_table_mode="accurate",
        default_chunker="hybrid",
        default_chunk_max_tokens=512,
        default_chunk_tokenizer="sentence-transformers/all-MiniLM-L6-v2",
        enable_legacy_xls=enable_legacy_xls,
        storage_path=Path("storage/documents"),
        database_url="sqlite:///app.db",
    )


class ParserFactoryTest(unittest.TestCase):
    def make_factory(self, *, enable_legacy_xls: bool = True) -> ParserFactory:
        return ParserFactory(
            make_config(enable_legacy_xls=enable_legacy_xls),
            docling_parser_builder=DummyDoclingParser,
            text_parser_builder=DummyTextParser,
        )

    def test_docling_extensions_return_docling_parser(self):
        factory = self.make_factory()

        for extension in [".pdf", ".docx", ".md", ".xlsx", ".xls", ".csv"]:
            with self.subTest(extension=extension):
                self.assertIsInstance(factory.get(extension), DummyDoclingParser)

    def test_text_extension_returns_text_parser(self):
        factory = self.make_factory()

        self.assertIsInstance(factory.get(".txt"), DummyTextParser)

    def test_extension_matching_is_case_insensitive(self):
        factory = self.make_factory()

        self.assertIsInstance(factory.get(".PDF"), DummyDoclingParser)
        self.assertIsInstance(factory.get(".TXT"), DummyTextParser)

    def test_unsupported_extension_fails_before_parser_selection(self):
        factory = self.make_factory()

        with self.assertRaises(UnsupportedFileTypeError):
            factory.get(".exe")

    def test_legacy_xls_can_be_disabled(self):
        factory = self.make_factory(enable_legacy_xls=False)

        with self.assertRaises(UnsupportedFileTypeError):
            factory.get(".xls")


if __name__ == "__main__":
    unittest.main()
