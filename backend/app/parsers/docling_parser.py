from pathlib import Path
from typing import Any

from ..models.parsed_document import ParsedDocument
from ..services.docling_service import DoclingService
from ..utils.errors import AppError, ErrorCode
from .base import DocumentParser


class DoclingParser(DocumentParser):
    def __init__(self, docling_service: DoclingService | None = None):
        self.docling_service = docling_service

    def parse(self, file_path: str | Path) -> ParsedDocument:
        if self.docling_service is None:
            raise AppError(
                code=ErrorCode.DOCLING_INITIALIZATION_FAILED,
                message="Docling parser requires a DoclingService.",
            )

        path = Path(file_path)
        if path.suffix.lower() == ".xls":
            self.docling_service.ensure_xls_support()

        try:
            document = self.docling_service.convert(path)
        except AppError:
            raise
        except Exception as error:
            raise AppError(
                code=ErrorCode.DOCUMENT_CONVERSION_FAILED,
                message="Unable to convert document with Docling.",
                details={"filename": path.name},
            ) from error

        markdown = export_document(document, "export_to_markdown")
        text = export_document(document, "export_to_text") or markdown
        metadata = extract_metadata(document, path)

        if not has_meaningful_content(markdown=markdown, text=text, metadata=metadata):
            raise AppError(
                code=ErrorCode.EMPTY_EXTRACTION,
                message="Docling conversion did not produce meaningful content.",
                details={"filename": path.name},
            )

        return ParsedDocument(
            source_format=path.suffix.lower().lstrip("."),
            structured_document=document,
            markdown=markdown,
            text=text,
            metadata=metadata,
        )


def export_document(document: Any, method_name: str) -> str:
    export_method = getattr(document, method_name, None)
    if not callable(export_method):
        return ""

    exported = export_method()
    return exported if isinstance(exported, str) else str(exported)


def extract_metadata(document: Any, path: Path) -> dict:
    return {
        "source_format": path.suffix.lower().lstrip("."),
        "page_count": collection_count(getattr(document, "pages", None)),
        "table_count": collection_count(getattr(document, "tables", None)),
        "picture_count": collection_count(getattr(document, "pictures", None)),
        "ocr_used": extract_ocr_used(document),
    }


def collection_count(value: Any) -> int | None:
    if value is None:
        return None

    if isinstance(value, dict | list | tuple | set):
        return len(value)

    try:
        return len(value)
    except TypeError:
        return None


def extract_ocr_used(document: Any) -> bool | None:
    for attribute in ("ocr_used", "used_ocr"):
        value = getattr(document, attribute, None)
        if isinstance(value, bool):
            return value

    metadata = getattr(document, "metadata", None)
    if isinstance(metadata, dict):
        for key in ("ocr_used", "used_ocr"):
            value = metadata.get(key)
            if isinstance(value, bool):
                return value

    return None


def has_meaningful_content(*, markdown: str, text: str, metadata: dict) -> bool:
    if markdown.strip() or text.strip():
        return True

    for key in ("page_count", "table_count", "picture_count"):
        count = metadata.get(key)
        if isinstance(count, int) and count > 0:
            return True

    return False
