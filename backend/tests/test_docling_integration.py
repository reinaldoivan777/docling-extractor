from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.app.config import AppConfig
from backend.app.models.parsed_document import ParsedDocument
from backend.app.services.chunking_service import ChunkingService
from backend.app.services.docling_service import DoclingService


FIXTURES = Path(__file__).parent / "fixtures"


def make_config(root: Path) -> AppConfig:
    return AppConfig(
        flask_env="test",
        allowed_extensions={".pdf", ".docx", ".txt", ".md", ".xlsx", ".xls", ".csv"},
        max_upload_size_mb=20,
        max_document_pages=200,
        document_processing_timeout_seconds=120,
        docling_ocr_enabled=False,
        docling_force_ocr=False,
        docling_table_structure_enabled=True,
        docling_table_mode="accurate",
        default_chunker="hybrid",
        default_chunk_max_tokens=64,
        default_chunk_tokenizer="sentence-transformers/all-MiniLM-L6-v2",
        enable_legacy_xls=False,
        storage_path=root / "documents",
        database_url=f"sqlite:///{root / 'app.db'}",
    )


class FixtureInventoryTest(unittest.TestCase):
    def test_required_fixtures_exist(self):
        expected = [
            "sample.pdf",
            "sample-scanned.pdf",
            "sample-table.pdf",
            "sample.docx",
            "sample.txt",
            "sample.md",
            "sample.xlsx",
            "sample.csv",
            "sample.xls",
        ]

        for filename in expected:
            with self.subTest(filename=filename):
                path = FIXTURES / filename
                self.assertTrue(path.exists())
                self.assertGreater(path.stat().st_size, 0)


class DoclingIntegrationTest(unittest.TestCase):
    def test_docling_converts_markdown_fixture_and_hybrid_chunker_consumes_document(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = make_config(root)
            docling_service = DoclingService(config)

            readiness = docling_service.readiness()
            if not readiness.ready:
                self.skipTest(readiness.error_message or "Docling is not ready.")

            docling_document = docling_service.convert(FIXTURES / "sample.md")
            markdown = docling_document.export_to_markdown()
            self.assertIn("Sample Markdown Fixture", markdown)

            parsed = ParsedDocument(
                source_format="md",
                structured_document=docling_document,
                markdown=markdown,
                text=docling_document.export_to_text(),
                metadata={"source_format": "md"},
            )
            chunks = ChunkingService(config).chunk(
                parsed,
                document_id="doc-integration",
                document_dir=root / "documents" / "doc-integration",
                filename="sample.md",
            )

            self.assertGreaterEqual(len(chunks), 1)
            self.assertIn("Sample Markdown Fixture", chunks[0].contextualized_content)
            self.assertEqual(chunks[0].metadata["source_format"], "md")
            self.assertTrue((root / "documents" / "doc-integration" / "chunks.json").exists())


if __name__ == "__main__":
    unittest.main()
