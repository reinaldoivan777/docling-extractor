from collections.abc import Iterable
from contextlib import closing
from datetime import UTC, datetime
import json
from pathlib import Path
import shutil
import sqlite3

from ..models.chunk import ChunkRecord
from ..models.document import DocumentRecord, DocumentStatus


def sqlite_path_from_url(database_url: str, base_dir: Path) -> Path:
    if database_url == "sqlite:///:memory:":
        return Path(":memory:")

    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("Only sqlite:/// database URLs are supported for the MVP.")

    database_path = Path(database_url[len(prefix) :])
    if database_path.is_absolute():
        return database_path

    return base_dir / database_path


class DocumentRepository:
    def __init__(self, database_path: Path, storage_path: Path):
        self.database_path = database_path
        self.storage_path = storage_path

    def init_db(self) -> None:
        if self.database_path != Path(":memory:"):
            self.database_path.parent.mkdir(parents=True, exist_ok=True)

        with closing(self.connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    extension TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    page_count INTEGER,
                    table_count INTEGER,
                    picture_count INTEGER,
                    markdown_character_count INTEGER,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    ocr_used INTEGER,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    error_code TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    contextualized_content TEXT NOT NULL,
                    token_count INTEGER,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_chunks_document_order
                ON chunks (document_id, chunk_index);
                """
            )
            connection.commit()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create_document(
        self,
        *,
        document_id: str,
        filename: str,
        content_type: str,
        extension: str,
        size: int,
        metadata: dict | None = None,
    ) -> DocumentRecord:
        now = utc_now()
        metadata_json = encode_json(metadata or {})

        with closing(self.connect()) as connection:
            connection.execute(
                """
                INSERT INTO documents (
                    id, filename, content_type, extension, size, status,
                    metadata_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    filename,
                    content_type,
                    extension,
                    size,
                    DocumentStatus.UPLOADED.value,
                    metadata_json,
                    now,
                    now,
                ),
            )
            connection.commit()

        document = self.get_document(document_id)
        if document is None:
            raise RuntimeError("Document row was not created.")

        return document

    def update_document_status(
        self,
        document_id: str,
        status: DocumentStatus,
        *,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        with closing(self.connect()) as connection:
            connection.execute(
                """
                UPDATE documents
                SET status = ?, error_code = ?, error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                (status.value, error_code, error_message, utc_now(), document_id),
            )
            connection.commit()

    def save_processing_result(
        self,
        document_id: str,
        *,
        page_count: int | None = None,
        table_count: int | None = None,
        picture_count: int | None = None,
        markdown_character_count: int | None = None,
        chunk_count: int = 0,
        ocr_used: bool | None = None,
        metadata: dict | None = None,
        status: DocumentStatus = DocumentStatus.COMPLETED,
    ) -> None:
        with closing(self.connect()) as connection:
            connection.execute(
                """
                UPDATE documents
                SET status = ?,
                    page_count = ?,
                    table_count = ?,
                    picture_count = ?,
                    markdown_character_count = ?,
                    chunk_count = ?,
                    ocr_used = ?,
                    metadata_json = ?,
                    error_code = NULL,
                    error_message = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    status.value,
                    page_count,
                    table_count,
                    picture_count,
                    markdown_character_count,
                    chunk_count,
                    encode_bool(ocr_used),
                    encode_json(metadata or {}),
                    utc_now(),
                    document_id,
                ),
            )
            connection.commit()

    def save_chunks(self, document_id: str, chunks: Iterable[ChunkRecord]) -> None:
        now = utc_now()
        with closing(self.connect()) as connection:
            connection.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            connection.executemany(
                """
                INSERT INTO chunks (
                    id, document_id, chunk_index, content, contextualized_content,
                    token_count, metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.id,
                        document_id,
                        chunk.chunk_index,
                        chunk.content,
                        chunk.contextualized_content,
                        chunk.token_count,
                        encode_json(chunk.metadata),
                        now,
                    )
                    for chunk in chunks
                ],
            )
            connection.commit()

    def get_document(self, document_id: str) -> DocumentRecord | None:
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT * FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()

        return document_from_row(row) if row else None

    def list_chunks(self, document_id: str) -> list[ChunkRecord]:
        with closing(self.connect()) as connection:
            rows = connection.execute(
                """
                SELECT * FROM chunks
                WHERE document_id = ?
                ORDER BY chunk_index ASC
                """,
                (document_id,),
            ).fetchall()

        return [chunk_from_row(row) for row in rows]

    def delete_document(self, document_id: str, *, delete_artifacts: bool = True) -> bool:
        with closing(self.connect()) as connection:
            cursor = connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            deleted = cursor.rowcount > 0
            connection.commit()

        if deleted and delete_artifacts:
            shutil.rmtree(self.storage_path / document_id, ignore_errors=True)

        return deleted


def document_from_row(row: sqlite3.Row) -> DocumentRecord:
    return DocumentRecord(
        id=row["id"],
        filename=row["filename"],
        content_type=row["content_type"],
        extension=row["extension"],
        size=row["size"],
        status=DocumentStatus(row["status"]),
        page_count=row["page_count"],
        table_count=row["table_count"],
        picture_count=row["picture_count"],
        markdown_character_count=row["markdown_character_count"],
        chunk_count=row["chunk_count"],
        ocr_used=decode_bool(row["ocr_used"]),
        metadata=decode_json(row["metadata_json"]),
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def chunk_from_row(row: sqlite3.Row) -> ChunkRecord:
    return ChunkRecord(
        id=row["id"],
        document_id=row["document_id"],
        chunk_index=row["chunk_index"],
        content=row["content"],
        contextualized_content=row["contextualized_content"],
        token_count=row["token_count"],
        metadata=decode_json(row["metadata_json"]),
        created_at=row["created_at"],
    )


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def encode_json(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def decode_json(value: str | None) -> dict:
    if not value:
        return {}

    return json.loads(value)


def encode_bool(value: bool | None) -> int | None:
    if value is None:
        return None

    return 1 if value else 0


def decode_bool(value: int | None) -> bool | None:
    if value is None:
        return None

    return bool(value)
