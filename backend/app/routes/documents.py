from flask import Blueprint, current_app, jsonify, request

from ..repositories.document_repository import DocumentRepository
from ..utils.file import save_validated_upload

documents_bp = Blueprint("documents", __name__)


@documents_bp.post("/documents")
def upload_document():
    app_config = current_app.config["APP_CONFIG"]
    stored_upload = save_validated_upload(request.files, app_config)
    repository: DocumentRepository = current_app.extensions["document_repository"]
    document = repository.create_document(
        document_id=stored_upload.document_id,
        filename=stored_upload.display_filename,
        content_type=stored_upload.content_type,
        extension=stored_upload.extension,
        size=stored_upload.size,
        metadata={
            "original_path": str(stored_upload.original_path),
        },
    )

    return (
        jsonify(
            {
                "id": document.id,
                "filename": document.filename,
                "content_type": document.content_type,
                "extension": document.extension,
                "size": document.size,
                "status": document.status.value,
            }
        ),
        202,
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
