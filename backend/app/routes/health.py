from flask import Blueprint, current_app, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    app_config = current_app.config["APP_CONFIG"]
    docling = current_app.extensions["docling_service"].readiness()
    status = "ok" if docling.ready else "degraded"
    docling_payload = {
        "ready": docling.ready,
        "status": docling.status,
        "ocr_enabled": docling.ocr_enabled,
        "table_structure_enabled": docling.table_structure_enabled,
        "xls_support": docling.xls_support,
    }
    if docling.error_code:
        docling_payload["error_code"] = docling.error_code
        docling_payload["error_message"] = docling.error_message

    return jsonify(
        {
            "status": status,
            "services": {
                "api": "healthy",
                "docling": docling.status,
            },
            "docling": docling_payload,
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
