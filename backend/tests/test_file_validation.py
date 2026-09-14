from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from werkzeug.datastructures import FileStorage, MultiDict

from backend.app.config import AppConfig
from backend.app.utils.errors import (
    EmptyFileError,
    FileTooLargeError,
    InvalidFileError,
    UnsupportedFileTypeError,
)
from backend.app.utils.file import (
    safe_document_dir,
    sanitize_display_filename,
    save_validated_upload,
)


def make_config(root: Path, *, max_upload_size_mb: int = 1) -> AppConfig:
    return AppConfig(
        flask_env="test",
        allowed_extensions={".pdf", ".docx", ".txt", ".md", ".xlsx", ".xls", ".csv"},
        max_upload_size_mb=max_upload_size_mb,
        max_document_pages=200,
        document_processing_timeout_seconds=120,
        docling_ocr_enabled=True,
        docling_force_ocr=False,
        docling_table_structure_enabled=True,
        docling_table_mode="accurate",
        default_chunker="hybrid",
        default_chunk_max_tokens=512,
        default_chunk_tokenizer="sentence-transformers/all-MiniLM-L6-v2",
        enable_legacy_xls=True,
        storage_path=root / "documents",
        database_url=f"sqlite:///{root / 'app.db'}",
    )


def upload(filename: str, content: bytes, content_type: str = "text/plain") -> MultiDict:
    return MultiDict(
        {
            "file": FileStorage(
                stream=BytesIO(content),
                filename=filename,
                content_type=content_type,
            )
        }
    )


class FileValidationTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.config = make_config(self.root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_validated_upload_uses_generated_paths_and_sanitized_display_name(self):
        stored = save_validated_upload(
            upload("../unsafe note.txt", b"hello", "text/plain"),
            self.config,
        )

        self.assertEqual(stored.display_filename, "unsafe_note.txt")
        self.assertEqual(stored.extension, ".txt")
        self.assertEqual(stored.size, 5)
        self.assertEqual(stored.original_path.name, "original.txt")
        self.assertEqual(stored.original_path.read_bytes(), b"hello")
        self.assertTrue(stored.original_path.resolve().is_relative_to(self.config.storage_path.resolve()))
        self.assertNotIn("unsafe", stored.document_dir.name)

    def test_missing_file_field_is_invalid(self):
        with self.assertRaises(InvalidFileError):
            save_validated_upload(MultiDict(), self.config)

    def test_unsupported_extension_is_rejected(self):
        with self.assertRaises(UnsupportedFileTypeError):
            save_validated_upload(upload("payload.exe", b"hello"), self.config)

    def test_mime_mismatch_is_rejected(self):
        with self.assertRaises(UnsupportedFileTypeError):
            save_validated_upload(upload("sample.pdf", b"not a pdf", "text/plain"), self.config)

    def test_empty_file_is_rejected(self):
        with self.assertRaises(EmptyFileError):
            save_validated_upload(upload("empty.txt", b""), self.config)

    def test_file_larger_than_configured_limit_is_rejected(self):
        config = make_config(self.root, max_upload_size_mb=0)

        with self.assertRaises(FileTooLargeError):
            save_validated_upload(upload("sample.txt", b"x"), config)

    def test_safe_document_dir_rejects_path_traversal(self):
        with self.assertRaises(InvalidFileError):
            safe_document_dir(self.config.storage_path, "../escape")

    def test_empty_sanitized_filename_is_invalid(self):
        with self.assertRaises(InvalidFileError):
            sanitize_display_filename("...")


if __name__ == "__main__":
    unittest.main()
