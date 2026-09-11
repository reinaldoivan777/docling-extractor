from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from backend.app.models.parsed_document import ParsedDocument
from backend.app.services.serialization_service import SerializationService, normalize_text
from backend.app.utils.errors import AppError, ErrorCode


class FakeDoclingDocument:
    def __init__(self):
        self.export_dict_called = False

    def export_to_markdown(self):
        return "# Heading\r\n\r\nBody  \x00\r\n"

    def export_to_text(self):
        return "Heading\r\n\r\nBody  \x00\r\n"

    def export_to_dict(self):
        self.export_dict_called = True
        return {
            "texts": [{"text": "Body"}],
            "headings": ["Heading"],
            "tables": [],
        }


class BadExportDocument:
    def export_to_markdown(self):
        raise RuntimeError("boom")


class SerializationServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_docling_document_writes_json_markdown_and_text_artifacts(self):
        document = FakeDoclingDocument()
        parsed = ParsedDocument(
            source_format="pdf",
            structured_document=document,
            metadata={"page_count": 1},
        )
        service = SerializationService()

        serialized = service.serialize(parsed, self.root)

        self.assertEqual(serialized.markdown, "# Heading\n\nBody\n")
        self.assertEqual(serialized.text, "Heading\n\nBody\n")
        self.assertTrue((self.root / "document.md").exists())
        self.assertTrue((self.root / "document.txt").exists())
        self.assertTrue((self.root / "document.json").exists())
        self.assertTrue(document.export_dict_called)
        saved_json = json.loads((self.root / "document.json").read_text(encoding="utf-8"))
        self.assertEqual(saved_json["source_format"], "pdf")
        self.assertEqual(saved_json["metadata"], {"page_count": 1})
        self.assertEqual(saved_json["document"]["headings"], ["Heading"])

    def test_txt_document_writes_compatible_artifacts(self):
        parsed = ParsedDocument(
            source_format="txt",
            structured_document={
                "type": "text",
                "content": "A\r\nB\x00",
                "lines": ["A", "B"],
            },
            markdown="A\r\nB\x00",
            text="A\r\nB\x00",
            metadata={"character_count": 4, "line_count": 2},
        )
        service = SerializationService()

        serialized = service.serialize(parsed, self.root)

        self.assertEqual(serialized.markdown, "A\nB")
        self.assertEqual(serialized.text, "A\nB")
        self.assertEqual((self.root / "document.md").read_text(encoding="utf-8"), "A\nB")
        self.assertEqual((self.root / "document.txt").read_text(encoding="utf-8"), "A\nB")
        saved_json = json.loads((self.root / "document.json").read_text(encoding="utf-8"))
        self.assertEqual(saved_json["document"]["type"], "text")
        self.assertEqual(saved_json["metadata"]["line_count"], 2)

    def test_normalization_preserves_headings_and_paragraph_boundaries(self):
        text = "# Heading  \r\n\r\nParagraph one.  \rParagraph two.\x00"

        normalized = normalize_text(text)

        self.assertEqual(normalized, "# Heading\n\nParagraph one.\nParagraph two.")

    def test_optional_unicode_normalization(self):
        text = "ＡＢＣ"

        self.assertEqual(normalize_text(text), "ＡＢＣ")
        self.assertEqual(normalize_text(text, normalize_unicode=True), "ABC")

    def test_serialization_failure_maps_to_stable_error(self):
        parsed = ParsedDocument(source_format="pdf", structured_document=BadExportDocument())
        service = SerializationService()

        with self.assertRaises(AppError) as context:
            service.serialize(parsed, self.root)

        self.assertEqual(context.exception.code, ErrorCode.SERIALIZATION_FAILED)
        self.assertEqual(context.exception.message, "Unable to serialize parsed document.")


if __name__ == "__main__":
    unittest.main()
