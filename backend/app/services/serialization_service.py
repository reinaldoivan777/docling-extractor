from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import unicodedata

from ..models.parsed_document import ParsedDocument
from ..utils.errors import AppError, ErrorCode


@dataclass(frozen=True)
class SerializedDocument:
    markdown: str
    text: str
    structured_json: dict
    markdown_path: Path
    text_path: Path
    json_path: Path


class SerializationService:
    def __init__(self, *, normalize_unicode: bool = False):
        self.normalize_unicode = normalize_unicode

    def serialize(self, parsed_document: ParsedDocument, document_dir: str | Path) -> SerializedDocument:
        output_dir = Path(document_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            markdown = normalize_text(
                parsed_document.markdown or export_document(parsed_document.structured_document, "export_to_markdown"),
                normalize_unicode=self.normalize_unicode,
            )
            text = normalize_text(
                parsed_document.text
                or export_document(parsed_document.structured_document, "export_to_text")
                or markdown,
                normalize_unicode=self.normalize_unicode,
            )
            structured_json = structured_document_to_json(parsed_document)

            markdown_path = output_dir / "document.md"
            text_path = output_dir / "document.txt"
            json_path = output_dir / "document.json"

            markdown_path.write_text(markdown, encoding="utf-8")
            text_path.write_text(text, encoding="utf-8")
            json_path.write_text(
                json.dumps(structured_json, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )

            return SerializedDocument(
                markdown=markdown,
                text=text,
                structured_json=structured_json,
                markdown_path=markdown_path,
                text_path=text_path,
                json_path=json_path,
            )
        except AppError:
            raise
        except Exception as error:
            raise AppError(
                code=ErrorCode.SERIALIZATION_FAILED,
                message="Unable to serialize parsed document.",
            ) from error


def normalize_text(text: str, *, normalize_unicode: bool = False) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    normalized = "\n".join(line.rstrip() for line in normalized.split("\n"))

    if normalize_unicode:
        normalized = unicodedata.normalize("NFKC", normalized)

    return normalized


def export_document(document: Any, method_name: str) -> str:
    export_method = getattr(document, method_name, None)
    if not callable(export_method):
        return ""

    exported = export_method()
    return exported if isinstance(exported, str) else str(exported)


def structured_document_to_json(parsed_document: ParsedDocument) -> dict:
    structured = parsed_document.structured_document
    document_json = to_json_compatible(structured)

    return {
        "source_format": parsed_document.source_format,
        "metadata": to_json_compatible(parsed_document.metadata),
        "document": document_json,
    }


def to_json_compatible(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {str(key): to_json_compatible(item) for key, item in value.items()}

    if isinstance(value, list | tuple | set):
        return [to_json_compatible(item) for item in value]

    for method_name in ("export_to_dict", "to_dict", "model_dump"):
        method = getattr(value, method_name, None)
        if callable(method):
            return to_json_compatible(method())

    return {"type": type(value).__name__, "repr": repr(value)}
