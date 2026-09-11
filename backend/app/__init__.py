from flask import Flask
from flask_cors import CORS

from .config import load_config
from .routes.documents import documents_bp
from .routes.health import health_bp
from .utils.errors import register_error_handlers


def create_app() -> Flask:
    app = Flask(__name__)
    app_config = load_config()
    app.config["APP_CONFIG"] = app_config
    app.config["MAX_CONTENT_LENGTH"] = app_config.max_upload_size_bytes

    CORS(app)
    register_error_handlers(app)

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(documents_bp, url_prefix="/api")

    return app
