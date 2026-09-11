from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.app.models.parsed_document import ParsedDocument
from backend.app.parsers.text_parser import TextParser
from backend.app.utils.errors import AppError, ErrorCode


class TextParserTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.parser = TextParser()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_utf8_text(self):
        path = self.root / "sample.txt"
        path.write_text("Heading\n\nHello world\n", encoding="utf-8")

        parsed = self.parser.parse(path)

        self.assertIsInstance(parsed, ParsedDocument)
        self.assertEqual(parsed.source_format, "txt")
        self.assertEqual(parsed.text, "Heading\n\nHello world\n")
        self.assertEqual(parsed.markdown, "Heading\n\nHello world\n")
        self.assertEqual(parsed.structured_document["type"], "text")
        self.assertEqual(parsed.structured_document["lines"], ["Heading", "", "Hello world"])
        self.assertEqual(parsed.metadata["source_format"], "txt")
        self.assertEqual(parsed.metadata["character_count"], 21)
        self.assertEqual(parsed.metadata["line_count"], 3)

    def test_parse_unreadable_text_returns_conversion_error(self):
        path = self.root / "bad.txt"
        path.write_bytes(b"\xff\xfe\xfa")

        with self.assertRaises(AppError) as context:
            self.parser.parse(path)

        self.assertEqual(context.exception.code, ErrorCode.DOCUMENT_CONVERSION_FAILED)
        self.assertEqual(context.exception.message, "Unable to decode text file as UTF-8.")

    def test_parse_missing_file_returns_conversion_error(self):
        path = self.root / "missing.txt"

        with self.assertRaises(AppError) as context:
            self.parser.parse(path)

        self.assertEqual(context.exception.code, ErrorCode.DOCUMENT_CONVERSION_FAILED)
        self.assertEqual(context.exception.message, "Unable to read text file.")

    def test_empty_txt_is_left_to_upload_validation(self):
        path = self.root / "empty.txt"
        path.write_text("", encoding="utf-8")

        parsed = self.parser.parse(path)

        self.assertEqual(parsed.text, "")
        self.assertEqual(parsed.metadata["character_count"], 0)
        self.assertEqual(parsed.metadata["line_count"], 0)


if __name__ == "__main__":
    unittest.main()
