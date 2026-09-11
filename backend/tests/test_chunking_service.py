from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json
import unittest

from backend.app.config import AppConfig
from backend.app.models.parsed_document import ParsedDocument
from backend.app.services.chunking_service import ChunkingService, WhitespaceTokenizer
from backend.app.utils.errors import AppError, ErrorCode


class FakeDocItem:
    def __init__(self, *, self_ref: str, page_no: int | None = None, label: str = "text"):
        self.self_ref = self_ref
        self.label = label
        self.prov = []
        if page_no is not None:
            self.prov.append(SimpleNamespace(page_no=page_no))


class FakeDocChunk:
    def __init__(self, text: str, meta):
        self.text = text
        self.meta = meta


class FakeHybridChunker:
    last_tokenizer = None

    def __init__(self, tokenizer):
        type(self).last_tokenizer = tokenizer

    def chunk(self, dl_doc):
        return dl_doc["chunks"]

    def contextualize(self, chunk):
        headings = chunk.meta.headings or []
        prefix = "\n".join(f"Heading: {heading}" for heading in headings)
        return f"{prefix}\n\n{chunk.text}" if prefix else chunk.text


class FakeHierarchicalChunker:
    def chunk(self, dl_doc):
        return dl_doc["chunks"]

    def contextualize(self, chunk):
        return chunk.text


def make_config() -> AppConfig:
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
        default_chunk_max_tokens=3,
        default_chunk_tokenizer="sentence-transformers/all-MiniLM-L6-v2",
        enable_legacy_xls=True,
        storage_path=Path("storage/documents"),
        database_url="sqlite:///app.db",
    )


class ChunkingServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_text_document_chunks_with_token_limit_and_writes_json(self):
        parsed = ParsedDocument(
            source_format="txt",
            structured_document={"type": "text", "content": "one two three four five"},
            text="one two three four five",
        )
        service = ChunkingService(make_config())

        chunks = service.chunk(
            parsed,
            document_id="doc-1",
            document_dir=self.root,
            filename="note.txt",
        )

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].content, "one two three")
        self.assertEqual(chunks[0].token_count, 3)
        self.assertEqual(chunks[1].content, "four five")
        self.assertEqual(chunks[0].metadata["filename"], "note.txt")
        saved = json.loads((self.root / "chunks.json").read_text(encoding="utf-8"))
        self.assertEqual(saved[0]["index"], 0)
        self.assertEqual(saved[1]["index"], 1)

    def test_docling_hybrid_chunker_maps_metadata_and_contextualizes(self):
        meta = SimpleNamespace(
            headings=["Financial Performance", "Revenue"],
            captions=["Table caption"],
            doc_items=[
                FakeDocItem(self_ref="#/texts/1", page_no=4),
                FakeDocItem(self_ref="#/tables/1", page_no=4, label="table"),
            ],
        )
        parsed = ParsedDocument(
            source_format="pdf",
            structured_document={"chunks": [FakeDocChunk("Revenue increased.", meta)]},
        )
        service = ChunkingService(make_config(), hybrid_chunker_cls=FakeHybridChunker)

        chunks = service.chunk(
            parsed,
            document_id="doc-1",
            document_dir=self.root,
            filename="report.pdf",
            max_tokens=8,
        )

        self.assertIsInstance(FakeHybridChunker.last_tokenizer, WhitespaceTokenizer)
        self.assertEqual(FakeHybridChunker.last_tokenizer.max_tokens, 8)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].content, "Revenue increased.")
        self.assertIn("Heading: Financial Performance", chunks[0].contextualized_content)
        self.assertEqual(chunks[0].metadata["headings"], ["Financial Performance", "Revenue"])
        self.assertEqual(chunks[0].metadata["page_numbers"], [4])
        self.assertEqual(chunks[0].metadata["captions"], ["Table caption"])
        self.assertEqual(chunks[0].metadata["table_refs"], ["#/tables/1"])
        self.assertEqual(chunks[0].metadata["source_items"], ["#/texts/1", "#/tables/1"])

    def test_hierarchical_chunker_option(self):
        meta = SimpleNamespace(headings=None, captions=None, doc_items=[])
        parsed = ParsedDocument(
            source_format="md",
            structured_document={"chunks": [FakeDocChunk("content", meta)]},
        )
        service = ChunkingService(make_config(), hierarchical_chunker_cls=FakeHierarchicalChunker)

        chunks = service.chunk(
            parsed,
            document_id="doc-1",
            document_dir=self.root,
            chunker="hierarchical",
        )

        self.assertEqual(chunks[0].content, "content")

    def test_unsupported_chunker_maps_to_chunking_failed(self):
        parsed = ParsedDocument(
            source_format="txt",
            structured_document={"type": "text", "content": "hello"},
            text="hello",
        )
        service = ChunkingService(make_config())

        with self.assertRaises(AppError) as context:
            service.chunk(parsed, document_id="doc-1", document_dir=self.root, chunker="unknown")

        self.assertEqual(context.exception.code, ErrorCode.CHUNKING_FAILED)

    def test_empty_text_document_maps_to_chunking_failed(self):
        parsed = ParsedDocument(source_format="txt", structured_document={"type": "text"}, text="")
        service = ChunkingService(make_config())

        with self.assertRaises(AppError) as context:
            service.chunk(parsed, document_id="doc-1", document_dir=self.root)

        self.assertEqual(context.exception.code, ErrorCode.CHUNKING_FAILED)


if __name__ == "__main__":
    unittest.main()
