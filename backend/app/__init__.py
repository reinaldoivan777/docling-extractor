from pathlib import Path

from flask import Flask
from flask_cors import CORS

from .config import load_config
from .repositories.document_repository import DocumentRepository, sqlite_path_from_url
from .routes.documents import documents_bp
from .routes.health import health_bp
from .parsers.factory import ParserFactory
from .services.chunking_service import ChunkingService
from .services.document_service import DocumentService
from .services.docling_service import DoclingService
from .services.serialization_service import SerializationService
from .utils.errors import register_error_handlers


def create_app() -> Flask:
    app = Flask(__name__)
    app_config = load_config()
    app.config["APP_CONFIG"] = app_config
    app.config["MAX_CONTENT_LENGTH"] = app_config.max_upload_size_bytes
    document_repository = DocumentRepository(
        database_path=sqlite_path_from_url(app_config.database_url, Path(app.instance_path)),
        storage_path=app_config.storage_path,
    )
    document_repository.init_db()
    app.extensions["document_repository"] = document_repository
    docling_service = DoclingService(app_config)
    app.extensions["docling_service"] = docling_service
    app.extensions["document_service"] = DocumentService(
        config=app_config,
        repository=document_repository,
        parser_factory=ParserFactory(app_config, docling_service=docling_service),
        serialization_service=SerializationService(),
        chunking_service=ChunkingService(app_config),
    )

    CORS(app)
    register_error_handlers(app)

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(documents_bp, url_prefix="/api")

    return app
