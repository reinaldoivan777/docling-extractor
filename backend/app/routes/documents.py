import json

from flask import Blueprint, current_app, jsonify, request

from ..models.chunk import ChunkRecord
from ..models.document import DocumentRecord
from ..repositories.document_repository import DocumentRepository
from ..services.document_service import DocumentService
from ..utils.errors import DocumentNotFoundError, InvalidFileError

documents_bp = Blueprint("documents", __name__)


@documents_bp.post("/documents")
def upload_document():
    document_service: DocumentService = current_app.extensions["document_service"]
    result = document_service.process_upload(
        request.files,
        chunker=request.form.get("chunker"),
        max_tokens=parse_optional_int(request.form.get("max_tokens")),
    )
    document = result.document

    return jsonify(
        {
            "id": document.id,
            "filename": document.filename,
            "content_type": document.content_type,
            "extension": document.extension,
            "size": document.size,
            "status": document.status.value,
            "metadata": document.metadata,
            "chunk_count": result.chunk_count,
        }
    )


@documents_bp.delete("/documents/<document_id>")
def delete_document(document_id: str):
    repository: DocumentRepository = current_app.extensions["document_repository"]
    deleted = repository.delete_document(document_id)

    if not deleted:
        raise DocumentNotFoundError()

    return jsonify({"success": True})


@documents_bp.get("/documents/<document_id>")
def get_document(document_id: str):
    repository: DocumentRepository = current_app.extensions["document_repository"]
    document = repository.get_document(document_id)

    if document is None:
        raise DocumentNotFoundError()

    return jsonify(document_payload(document))


@documents_bp.get("/documents/<document_id>/content")
def get_document_content(document_id: str):
    repository: DocumentRepository = current_app.extensions["document_repository"]
    document = get_existing_document(repository, document_id)
    document_dir = repository.storage_path / document.id

    markdown_path = document_dir / "document.md"
    text_path = document_dir / "document.txt"

    return jsonify(
        {
            "document_id": document.id,
            "markdown": read_text_if_exists(markdown_path),
            "text": read_text_if_exists(text_path),
            "available_exports": available_exports(document_dir),
        }
    )


@documents_bp.get("/documents/<document_id>/structure")
def get_document_structure(document_id: str):
    repository: DocumentRepository = current_app.extensions["document_repository"]
    document = get_existing_document(repository, document_id)
    document_dir = repository.storage_path / document.id
    structured_json = read_json_if_exists(document_dir / "document.json")
    metadata = document.metadata

    return jsonify(
        {
            "document_id": document.id,
            "pages": document.page_count,
            "tables": document.table_count,
            "pictures": document.picture_count,
            "headings": extract_headings(structured_json),
            "source_format": document.extension.lstrip("."),
            "metadata": {
                "ocr_used": document.ocr_used,
                "markdown_character_count": document.markdown_character_count,
                "chunk_count": document.chunk_count,
                "artifacts": metadata.get("artifacts", {}),
            },
        }
    )


@documents_bp.get("/documents/<document_id>/chunks")
def get_document_chunks(document_id: str):
    repository: DocumentRepository = current_app.extensions["document_repository"]
    document = get_existing_document(repository, document_id)
    chunks = repository.list_chunks(document.id)

    return jsonify(
        {
            "document_id": document.id,
            "count": len(chunks),
            "chunks": [chunk_payload(chunk) for chunk in chunks],
        }
    )


def parse_optional_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None

    try:
        parsed = int(value)
    except ValueError as error:
        raise InvalidFileError("max_tokens must be an integer.") from error

    if parsed < 1:
        raise InvalidFileError("max_tokens must be greater than zero.")

    return parsed


def get_existing_document(repository: DocumentRepository, document_id: str) -> DocumentRecord:
    document = repository.get_document(document_id)
    if document is None:
        raise DocumentNotFoundError()

    return document


def document_payload(document: DocumentRecord) -> dict:
    return {
        "id": document.id,
        "filename": document.filename,
        "content_type": document.content_type,
        "extension": document.extension,
        "size": document.size,
        "status": document.status.value,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "processing": {
            "page_count": document.page_count,
            "markdown_character_count": document.markdown_character_count,
            "chunk_count": document.chunk_count,
            "ocr_used": document.ocr_used,
            "table_count": document.table_count,
            "picture_count": document.picture_count,
        },
        "metadata": document.metadata,
        "error": {
            "code": document.error_code,
            "message": document.error_message,
        }
        if document.error_code
        else None,
    }


def chunk_payload(chunk: ChunkRecord) -> dict:
    return {
        "id": chunk.id,
        "document_id": chunk.document_id,
        "index": chunk.chunk_index,
        "content": chunk.content,
        "contextualized_content": chunk.contextualized_content,
        "token_count": chunk.token_count,
        "metadata": chunk.metadata,
        "created_at": chunk.created_at,
    }


def read_text_if_exists(path):
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_json_if_exists(path):
    if not path.exists():
        return {}

    return json.loads(path.read_text(encoding="utf-8"))


def available_exports(document_dir) -> list[str]:
    exports: list[str] = []
    if (document_dir / "document.md").exists():
        exports.append("markdown")
    if (document_dir / "document.txt").exists():
        exports.append("text")
    if (document_dir / "document.json").exists():
        exports.append("json")

    return exports


def extract_headings(structured_json: dict) -> list[str]:
    document = structured_json.get("document", {})
    headings = document.get("headings")
    if isinstance(headings, list):
        return [str(heading) for heading in headings]

    return []
