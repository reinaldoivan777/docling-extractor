from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from backend.app import create_app


class DocumentsApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.env_patch = patch.dict(
            "os.environ",
            {
                "DATABASE_URL": f"sqlite:///{self.root / 'app.db'}",
                "STORAGE_PATH": str(self.root / "documents"),
            },
        )
        self.env_patch.start()
        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def upload_txt(self, *, content: bytes = b"# Heading\n\none two three four", filename: str = "note.txt"):
        return self.client.post(
            "/api/documents",
            data={
                "file": (BytesIO(content), filename),
                "max_tokens": "3",
            },
            content_type="multipart/form-data",
        )

    def test_upload_get_content_structure_chunks_and_delete(self):
        upload = self.upload_txt()

        self.assertEqual(upload.status_code, 200)
        self.assertEqual(upload.json["status"], "COMPLETED")
        self.assertEqual(upload.json["chunk_count"], 2)
        self.assertIn("metadata", upload.json)
        document_id = upload.json["id"]

        document = self.client.get(f"/api/documents/{document_id}")
        self.assertEqual(document.status_code, 200)
        self.assertEqual(document.json["id"], document_id)
        self.assertEqual(document.json["processing"]["chunk_count"], 2)

        content = self.client.get(f"/api/documents/{document_id}/content")
        self.assertEqual(content.status_code, 200)
        self.assertEqual(content.json["document_id"], document_id)
        self.assertIn("markdown", content.json["available_exports"])
        self.assertIn("text", content.json["available_exports"])
        self.assertIn("json", content.json["available_exports"])
        self.assertIn("# Heading", content.json["markdown"])

        structure = self.client.get(f"/api/documents/{document_id}/structure")
        self.assertEqual(structure.status_code, 200)
        self.assertEqual(structure.json["document_id"], document_id)
        self.assertEqual(structure.json["source_format"], "txt")
        self.assertEqual(structure.json["metadata"]["chunk_count"], 2)

        chunks = self.client.get(f"/api/documents/{document_id}/chunks")
        self.assertEqual(chunks.status_code, 200)
        self.assertEqual(chunks.json["count"], 2)
        self.assertEqual([chunk["index"] for chunk in chunks.json["chunks"]], [0, 1])
        self.assertIn("contextualized_content", chunks.json["chunks"][0])

        delete = self.client.delete(f"/api/documents/{document_id}")
        self.assertEqual(delete.status_code, 200)
        self.assertEqual(delete.json, {"success": True})
        self.assertFalse((self.root / "documents" / document_id).exists())

    def test_missing_document_endpoints_return_document_not_found(self):
        for path in [
            "/api/documents/missing",
            "/api/documents/missing/content",
            "/api/documents/missing/structure",
            "/api/documents/missing/chunks",
        ]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json["error"]["code"], "DOCUMENT_NOT_FOUND")

        delete = self.client.delete("/api/documents/missing")
        self.assertEqual(delete.status_code, 404)
        self.assertEqual(delete.json["error"]["code"], "DOCUMENT_NOT_FOUND")

    def test_invalid_max_tokens_uses_json_error_envelope(self):
        response = self.client.post(
            "/api/documents",
            data={
                "file": (BytesIO(b"hello"), "note.txt"),
                "max_tokens": "abc",
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"]["code"], "INVALID_FILE")
        self.assertEqual(response.json["error"]["message"], "max_tokens must be an integer.")


if __name__ == "__main__":
    unittest.main()
