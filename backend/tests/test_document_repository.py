from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from backend.app import create_app
from backend.app.models.chunk import ChunkRecord
from backend.app.models.document import DocumentStatus
from backend.app.repositories.document_repository import DocumentRepository


class DocumentRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.repository = DocumentRepository(
            database_path=self.root / "app.db",
            storage_path=self.root / "documents",
        )
        self.repository.init_db()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_and_update_document_status(self):
        document = self.repository.create_document(
            document_id="doc-1",
            filename="report.pdf",
            content_type="application/pdf",
            extension=".pdf",
            size=123,
            metadata={"source": "unit"},
        )

        self.assertEqual(document.status, DocumentStatus.UPLOADED)
        self.assertEqual(document.metadata, {"source": "unit"})

        self.repository.update_document_status("doc-1", DocumentStatus.CONVERTING)
        updated = self.repository.get_document("doc-1")

        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, DocumentStatus.CONVERTING)

    def test_save_chunks_returns_ordered_by_chunk_index(self):
        self.repository.create_document(
            document_id="doc-1",
            filename="report.pdf",
            content_type="application/pdf",
            extension=".pdf",
            size=123,
        )
        self.repository.save_chunks(
            "doc-1",
            [
                ChunkRecord(
                    id="chunk-2",
                    document_id="doc-1",
                    chunk_index=2,
                    content="second",
                    contextualized_content="second",
                ),
                ChunkRecord(
                    id="chunk-1",
                    document_id="doc-1",
                    chunk_index=1,
                    content="first",
                    contextualized_content="first",
                    metadata={"page_numbers": [1]},
                ),
            ],
        )

        chunks = self.repository.list_chunks("doc-1")

        self.assertEqual([chunk.chunk_index for chunk in chunks], [1, 2])
        self.assertEqual(chunks[0].metadata, {"page_numbers": [1]})

    def test_save_processing_result_persists_metrics(self):
        self.repository.create_document(
            document_id="doc-1",
            filename="report.pdf",
            content_type="application/pdf",
            extension=".pdf",
            size=123,
        )

        self.repository.save_processing_result(
            "doc-1",
            page_count=10,
            table_count=2,
            picture_count=1,
            markdown_character_count=1200,
            chunk_count=4,
            ocr_used=False,
            metadata={"duration_ms": 99},
        )
        document = self.repository.get_document("doc-1")

        self.assertEqual(document.status, DocumentStatus.COMPLETED)
        self.assertEqual(document.page_count, 10)
        self.assertEqual(document.chunk_count, 4)
        self.assertFalse(document.ocr_used)
        self.assertEqual(document.metadata, {"duration_ms": 99})

    def test_delete_document_removes_rows_and_artifacts(self):
        self.repository.create_document(
            document_id="doc-1",
            filename="report.pdf",
            content_type="application/pdf",
            extension=".pdf",
            size=123,
        )
        self.repository.save_chunks(
            "doc-1",
            [
                ChunkRecord(
                    id="chunk-1",
                    document_id="doc-1",
                    chunk_index=0,
                    content="content",
                    contextualized_content="content",
                )
            ],
        )
        artifact_dir = self.root / "documents" / "doc-1"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "original.pdf").write_text("content", encoding="utf-8")

        deleted = self.repository.delete_document("doc-1")

        self.assertTrue(deleted)
        self.assertIsNone(self.repository.get_document("doc-1"))
        self.assertEqual(self.repository.list_chunks("doc-1"), [])
        self.assertFalse(artifact_dir.exists())


class UploadPersistenceTest(unittest.TestCase):
    def test_upload_stub_creates_document_row(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with patch.dict(
                "os.environ",
                {
                    "DATABASE_URL": f"sqlite:///{root / 'app.db'}",
                    "STORAGE_PATH": str(root / "documents"),
                },
            ):
                app = create_app()
                client = app.test_client()

                response = client.post(
                    "/api/documents",
                    data={"file": (BytesIO(b"hello"), "note.txt")},
                    content_type="multipart/form-data",
                )

                self.assertEqual(response.status_code, 200)
                document_id = response.json["id"]
                repository = app.extensions["document_repository"]
                document = repository.get_document(document_id)

                self.assertIsNotNone(document)
                self.assertEqual(document.filename, "note.txt")
                self.assertEqual(document.status, DocumentStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()
