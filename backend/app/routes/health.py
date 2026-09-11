from flask import Blueprint, current_app, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    app_config = current_app.config["APP_CONFIG"]

    return jsonify(
        {
            "status": "ok",
            "services": {
                "api": "healthy",
                "docling": "not_configured",
            },
            "config": {
                "max_upload_size_mb": app_config.max_upload_size_mb,
                "max_document_pages": app_config.max_document_pages,
                "processing_timeout_seconds": app_config.document_processing_timeout_seconds,
                "default_chunker": app_config.default_chunker,
                "default_chunk_max_tokens": app_config.default_chunk_max_tokens,
                "legacy_xls_enabled": app_config.enable_legacy_xls,
            },
        }
    )
