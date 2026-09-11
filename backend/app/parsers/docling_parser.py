from pathlib import Path

from ..models.parsed_document import ParsedDocument
from ..utils.errors import AppError, ErrorCode
from .base import DocumentParser


class DoclingParser(DocumentParser):
    def parse(self, file_path: str | Path) -> ParsedDocument:
        raise AppError(
            code=ErrorCode.DOCUMENT_CONVERSION_FAILED,
            message="Docling parser is not implemented yet.",
        )
