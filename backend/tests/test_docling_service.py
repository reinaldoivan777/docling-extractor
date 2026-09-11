from pathlib import Path
from enum import StrEnum
from types import ModuleType, SimpleNamespace
import sys
import unittest
from unittest.mock import patch

from backend.app.config import AppConfig
from backend.app.services.docling_service import DoclingService
from backend.app.utils.errors import AppError, ErrorCode


class FakeInputFormat:
    PDF = "pdf"


class FakePdfPipelineOptions:
    def __init__(self):
        self.do_ocr = False
        self.do_table_structure = False
        self.table_structure_options = SimpleNamespace(mode=None)


class FakeTableFormerMode(StrEnum):
    FAST = "fast"
    ACCURATE = "accurate"


class FakePdfFormatOption:
    def __init__(self, pipeline_options):
        self.pipeline_options = pipeline_options


class FakeDocumentConverter:
    instances = 0

    def __init__(self, format_options):
        type(self).instances += 1
        self.format_options = format_options

    def convert(self, file_path):
        return SimpleNamespace(document={"converted": file_path})


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


def fake_docling_modules():
    base_models = ModuleType("docling.datamodel.base_models")
    base_models.InputFormat = FakeInputFormat

    pipeline_options = ModuleType("docling.datamodel.pipeline_options")
    pipeline_options.PdfPipelineOptions = FakePdfPipelineOptions
    pipeline_options.TableFormerMode = FakeTableFormerMode

    document_converter = ModuleType("docling.document_converter")
    document_converter.DocumentConverter = FakeDocumentConverter
    document_converter.PdfFormatOption = FakePdfFormatOption

    return {
        "docling": ModuleType("docling"),
        "docling.datamodel": ModuleType("docling.datamodel"),
        "docling.datamodel.base_models": base_models,
        "docling.datamodel.pipeline_options": pipeline_options,
        "docling.document_converter": document_converter,
    }


class DoclingServiceTest(unittest.TestCase):
    def setUp(self):
        FakeDocumentConverter.instances = 0

    def test_initializes_converter_once_and_reports_ready(self):
        with patch.dict(sys.modules, fake_docling_modules()), patch("shutil.which", return_value="/usr/bin/soffice"):
            service = DoclingService(make_config())

        readiness = service.readiness()

        self.assertTrue(readiness.ready)
        self.assertEqual(readiness.status, "ready")
        self.assertTrue(readiness.ocr_enabled)
        self.assertTrue(readiness.table_structure_enabled)
        self.assertTrue(readiness.xls_support)
        self.assertEqual(FakeDocumentConverter.instances, 1)

    def test_convert_returns_docling_document(self):
        with patch.dict(sys.modules, fake_docling_modules()), patch("shutil.which", return_value="/usr/bin/soffice"):
            service = DoclingService(make_config())
            converted = service.convert("sample.pdf")

        self.assertEqual(converted, {"converted": "sample.pdf"})
        self.assertEqual(FakeDocumentConverter.instances, 1)

    def test_import_failure_reports_degraded_readiness_and_raises_on_converter_access(self):
        blocked_modules = {
            name: None
            for name in [
                "docling",
                "docling.datamodel",
                "docling.datamodel.base_models",
                "docling.datamodel.pipeline_options",
                "docling.document_converter",
            ]
        }

        with patch.dict(sys.modules, blocked_modules):
            service = DoclingService(make_config())

        readiness = service.readiness()

        self.assertFalse(readiness.ready)
        self.assertEqual(readiness.status, "initialization_failed")
        self.assertEqual(readiness.error_code, ErrorCode.DOCLING_INITIALIZATION_FAILED.value)
        with self.assertRaises(AppError) as context:
            _ = service.converter
        self.assertEqual(context.exception.code, ErrorCode.DOCLING_INITIALIZATION_FAILED)

    def test_missing_xls_runtime_is_detected(self):
        with patch.dict(sys.modules, fake_docling_modules()), patch("shutil.which", return_value=None):
            service = DoclingService(make_config())

        self.assertFalse(service.readiness().xls_support)
        with self.assertRaises(AppError) as context:
            service.ensure_xls_support()
        self.assertEqual(context.exception.code, ErrorCode.XLS_RUNTIME_UNAVAILABLE)

    def test_disabled_legacy_xls_does_not_raise_runtime_error(self):
        with patch.dict(sys.modules, fake_docling_modules()), patch("shutil.which", return_value=None):
            service = DoclingService(make_config(enable_legacy_xls=False))

        self.assertFalse(service.readiness().xls_support)
        service.ensure_xls_support()


if __name__ == "__main__":
    unittest.main()
