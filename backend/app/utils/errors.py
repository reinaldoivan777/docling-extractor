from dataclasses import dataclass
from enum import StrEnum
from http import HTTPStatus
from typing import Any

from flask import jsonify, request
from werkzeug.exceptions import HTTPException


class ErrorCode(StrEnum):
    INVALID_FILE = "INVALID_FILE"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    EMPTY_FILE = "EMPTY_FILE"
    DOCLING_INITIALIZATION_FAILED = "DOCLING_INITIALIZATION_FAILED"
    DOCUMENT_CONVERSION_FAILED = "DOCUMENT_CONVERSION_FAILED"
    EMPTY_EXTRACTION = "EMPTY_EXTRACTION"
    OCR_FAILED = "OCR_FAILED"
    XLS_RUNTIME_UNAVAILABLE = "XLS_RUNTIME_UNAVAILABLE"
    SERIALIZATION_FAILED = "SERIALIZATION_FAILED"
    CHUNKING_FAILED = "CHUNKING_FAILED"
    PROCESSING_TIMEOUT = "PROCESSING_TIMEOUT"
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


@dataclass
class AppError(Exception):
    code: ErrorCode
    message: str
    status_code: int = HTTPStatus.BAD_REQUEST
    details: dict[str, Any] | None = None


class InvalidFileError(AppError):
    def __init__(self, message: str = "Invalid file."):
        super().__init__(ErrorCode.INVALID_FILE, message, HTTPStatus.BAD_REQUEST)


class UnsupportedFileTypeError(AppError):
    def __init__(self, message: str = "This file type is not supported."):
        super().__init__(ErrorCode.UNSUPPORTED_FILE_TYPE, message, HTTPStatus.BAD_REQUEST)


class FileTooLargeError(AppError):
    def __init__(self, message: str = "File exceeds the maximum upload size."):
        super().__init__(ErrorCode.FILE_TOO_LARGE, message, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)


class EmptyFileError(AppError):
    def __init__(self, message: str = "Uploaded file is empty."):
        super().__init__(ErrorCode.EMPTY_FILE, message, HTTPStatus.BAD_REQUEST)


class DocumentNotFoundError(AppError):
    def __init__(self, message: str = "Document was not found."):
        super().__init__(ErrorCode.DOCUMENT_NOT_FOUND, message, HTTPStatus.NOT_FOUND)


def error_response(error: AppError):
    payload: dict[str, Any] = {
        "error": {
            "code": error.code.value,
            "message": error.message,
        }
    }

    if error.details:
        payload["error"]["details"] = error.details

    return jsonify(payload), int(error.status_code)


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        return error_response(error)

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        if not request.path.startswith("/api"):
            return error

        code = ErrorCode.INVALID_FILE
        if error.code == HTTPStatus.NOT_FOUND:
            code = ErrorCode.DOCUMENT_NOT_FOUND
        elif error.code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE:
            code = ErrorCode.FILE_TOO_LARGE

        return error_response(
            AppError(
                code=code,
                message=error.description,
                status_code=error.code or HTTPStatus.INTERNAL_SERVER_ERROR,
            )
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        if not request.path.startswith("/api"):
            raise error

        app.logger.exception("Unhandled API error")
        return error_response(
            AppError(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="An unexpected error occurred.",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
        )
