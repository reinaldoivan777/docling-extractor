from flask import Blueprint, current_app, jsonify, request

from ..repositories.document_repository import DocumentRepository
from ..services.document_service import DocumentService

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
            "chunk_count": result.chunk_count,
        }
    )


@documents_bp.delete("/documents/<document_id>")
def delete_document(document_id: str):
    repository: DocumentRepository = current_app.extensions["document_repository"]
    deleted = repository.delete_document(document_id)

    if not deleted:
        from ..utils.errors import DocumentNotFoundError

        raise DocumentNotFoundError()

    return jsonify({"success": True})


@documents_bp.get("/documents/<document_id>")
def get_document(document_id: str):
    repository: DocumentRepository = current_app.extensions["document_repository"]
    document = repository.get_document(document_id)

    if document is None:
        from ..utils.errors import DocumentNotFoundError

        raise DocumentNotFoundError()

    return jsonify(
        {
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
        }
    )


def parse_optional_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None

    return int(value)
