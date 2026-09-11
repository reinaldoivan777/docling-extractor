from flask import Flask
from flask_cors import CORS

from .routes.health import health_bp


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    app.register_blueprint(health_bp, url_prefix="/api")

    return app
