from dataclasses import dataclass
from pathlib import Path
import mimetypes
import uuid

from werkzeug.datastructures import FileStorage, MultiDict
from werkzeug.utils import secure_filename

from ..config import AppConfig
from .errors import (
    EmptyFileError,
    FileTooLargeError,
    InvalidFileError,
    UnsupportedFileTypeError,
)


ALLOWED_MIME_TYPES = {
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
    },
    ".txt": {"text/plain"},
    ".md": {"text/markdown", "text/plain"},
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
    },
    ".xls": {"application/vnd.ms-excel", "application/octet-stream"},
    ".csv": {"text/csv", "application/csv", "text/plain"},
}

GENERIC_MIME_TYPES = {"", "application/octet-stream", "binary/octet-stream"}


@dataclass(frozen=True)
class StoredUpload:
    document_id: str
    display_filename: str
    content_type: str
    extension: str
    size: int
    document_dir: Path
    original_path: Path


def save_validated_upload(files: MultiDict[str, FileStorage], config: AppConfig) -> StoredUpload:
    file = get_upload_file(files)
    display_filename = sanitize_display_filename(file.filename)
    extension = get_extension(display_filename)

    validate_extension(extension, config)
    validate_mime_type(file, extension)

    size = get_stream_size(file)
    validate_size(size, config)

    document_id = uuid.uuid4().hex
    document_dir = safe_document_dir(config.storage_path, document_id)
    document_dir.mkdir(parents=True, exist_ok=False)

    original_path = document_dir / f"original{extension}"
    file.stream.seek(0)
    file.save(original_path)

    return StoredUpload(
        document_id=document_id,
        display_filename=display_filename,
        content_type=file.content_type or guess_content_type(display_filename),
        extension=extension,
        size=size,
        document_dir=document_dir,
        original_path=original_path,
    )


def get_upload_file(files: MultiDict[str, FileStorage]) -> FileStorage:
    file = files.get("file")
    if file is None:
        raise InvalidFileError("Request must include a file field.")

    if not file.filename:
        raise InvalidFileError("Uploaded file must have a filename.")

    return file


def sanitize_display_filename(filename: str | None) -> str:
    if not filename:
        raise InvalidFileError("Uploaded file must have a filename.")

    sanitized = secure_filename(Path(filename).name)
    if not sanitized:
        raise InvalidFileError("Uploaded file must have a valid filename.")

    return sanitized


def get_extension(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if not extension:
        raise UnsupportedFileTypeError("Uploaded file must have an extension.")

    return extension


def validate_extension(extension: str, config: AppConfig) -> None:
    if extension not in config.allowed_extensions:
        raise UnsupportedFileTypeError()


def validate_mime_type(file: FileStorage, extension: str) -> None:
    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    if content_type in GENERIC_MIME_TYPES:
        return

    allowed_types = ALLOWED_MIME_TYPES.get(extension, set())
    guessed_type = guess_content_type(file.filename or "")
    if content_type not in allowed_types and content_type != guessed_type:
        raise UnsupportedFileTypeError("Uploaded file MIME type does not match its extension.")


def guess_content_type(filename: str) -> str:
    guessed_type, _ = mimetypes.guess_type(filename)
    return guessed_type or "application/octet-stream"


def get_stream_size(file: FileStorage) -> int:
    stream = file.stream
    current_position = stream.tell()
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(current_position)
    return size


def validate_size(size: int, config: AppConfig) -> None:
    if size <= 0:
        raise EmptyFileError()

    if size > config.max_upload_size_bytes:
        raise FileTooLargeError()


def safe_document_dir(storage_path: Path, document_id: str) -> Path:
    storage_root = storage_path.resolve()
    document_dir = (storage_root / document_id).resolve()

    if storage_root not in document_dir.parents:
        raise InvalidFileError("Invalid storage path.")

    return document_dir
