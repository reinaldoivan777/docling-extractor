from flask import Blueprint, current_app, jsonify, request

from ..utils.file import save_validated_upload

documents_bp = Blueprint("documents", __name__)


@documents_bp.post("/documents")
def upload_document():
    app_config = current_app.config["APP_CONFIG"]
    stored_upload = save_validated_upload(request.files, app_config)

    return (
        jsonify(
            {
                "id": stored_upload.document_id,
                "filename": stored_upload.display_filename,
                "content_type": stored_upload.content_type,
                "extension": stored_upload.extension,
                "size": stored_upload.size,
                "status": "UPLOADED",
            }
        ),
        202,
    )
