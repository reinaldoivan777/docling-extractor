from pathlib import Path

from ..models.parsed_document import ParsedDocument
from ..utils.errors import AppError, ErrorCode
from .base import DocumentParser


class TextParser(DocumentParser):
    def parse(self, file_path: str | Path) -> ParsedDocument:
        path = Path(file_path)

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise AppError(
                code=ErrorCode.DOCUMENT_CONVERSION_FAILED,
                message="Unable to decode text file as UTF-8.",
                details={"filename": path.name},
            ) from error
        except OSError as error:
            raise AppError(
                code=ErrorCode.DOCUMENT_CONVERSION_FAILED,
                message="Unable to read text file.",
                details={"filename": path.name},
            ) from error

        lines = text.splitlines()
        structured_document = {
            "type": "text",
            "content": text,
            "lines": lines,
        }
        metadata = {
            "source_format": "txt",
            "character_count": len(text),
            "line_count": len(lines),
        }

        return ParsedDocument(
            source_format="txt",
            structured_document=structured_document,
            markdown=text,
            text=text,
            metadata=metadata,
        )
