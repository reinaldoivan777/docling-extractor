from dataclasses import dataclass
from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE_DIR.parent


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default

    return int(value)


@dataclass(frozen=True)
class AppConfig:
    flask_env: str
    allowed_extensions: set[str]
    max_upload_size_mb: int
    max_document_pages: int
    document_processing_timeout_seconds: int
    docling_ocr_enabled: bool
    docling_force_ocr: bool
    docling_table_structure_enabled: bool
    docling_table_mode: str
    default_chunker: str
    default_chunk_max_tokens: int
    default_chunk_tokenizer: str
    enable_legacy_xls: bool
    storage_path: Path
    database_url: str

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


def load_config() -> AppConfig:
    load_env_file(PROJECT_ROOT / ".env")
    load_env_file(BASE_DIR / ".env")

    storage_path = Path(os.environ.get("STORAGE_PATH", "./storage/documents"))
    if not storage_path.is_absolute():
        storage_path = BASE_DIR / storage_path

    return AppConfig(
        flask_env=os.environ.get("FLASK_ENV", "development"),
        allowed_extensions={".pdf", ".docx", ".txt", ".md", ".xlsx", ".xls", ".csv"},
        max_upload_size_mb=env_int("MAX_UPLOAD_SIZE_MB", 20),
        max_document_pages=env_int("MAX_DOCUMENT_PAGES", 200),
        document_processing_timeout_seconds=env_int(
            "DOCUMENT_PROCESSING_TIMEOUT_SECONDS",
            120,
        ),
        docling_ocr_enabled=env_bool("DOCLING_OCR_ENABLED", True),
        docling_force_ocr=env_bool("DOCLING_FORCE_OCR", False),
        docling_table_structure_enabled=env_bool(
            "DOCLING_TABLE_STRUCTURE_ENABLED",
            True,
        ),
        docling_table_mode=os.environ.get("DOCLING_TABLE_MODE", "accurate"),
        default_chunker=os.environ.get("DEFAULT_CHUNKER", "hybrid"),
        default_chunk_max_tokens=env_int("DEFAULT_CHUNK_MAX_TOKENS", 512),
        default_chunk_tokenizer=os.environ.get(
            "DEFAULT_CHUNK_TOKENIZER",
            "sentence-transformers/all-MiniLM-L6-v2",
        ),
        enable_legacy_xls=env_bool("ENABLE_LEGACY_XLS", True),
        storage_path=storage_path,
        database_url=os.environ.get("DATABASE_URL", "sqlite:///app.db"),
    )
