# Architecture

## Overview

Document RAG Processor is a React + Flask application for turning uploaded documents into structured, RAG-ready chunks.

For the MVP, Docling runs in the same Python process as Flask. This keeps the deployment small while preserving access to `DoclingDocument`, metadata, serialization, and Docling chunking APIs.

```text
Browser
  -> React frontend
  -> Flask API
  -> DocumentService
  -> ParserFactory
     -> DoclingParser
     -> TextParser
  -> SerializationService
  -> ChunkingService
  -> SQLite + local filesystem
```

## Key Decisions

| Area | MVP Decision | Reason |
|---|---|---|
| Docling deployment | In-process Python library | Avoids extra parser service for MVP |
| Canonical representation | `DoclingDocument` | Preserves layout, hierarchy, tables, and provenance |
| TXT parsing | Native Python | Plain text does not need Docling |
| Chunking | Docling `HybridChunker` | Structure-aware and token-aware |
| Persistence | SQLite + local filesystem | Simple and inspectable |
| Processing mode | Synchronous | Simplest path for MVP |
| Legacy XLS | Optional with LibreOffice | Requires extra runtime support |

## System Flow

```text
Upload
  -> Validate file
  -> Save original artifact
  -> Create document row with UPLOADED status
  -> Select parser by extension
  -> Convert to structured document
  -> Serialize to Markdown/Text/JSON
  -> Chunk from structured representation
  -> Persist outputs and metrics
  -> Return document summary
```

Document statuses:

```text
UPLOADED
CONVERTING
NORMALIZING
CHUNKING
COMPLETED
FAILED
```

## Component Responsibilities

### React Frontend

The frontend provides a compact inspection workflow:

- upload supported documents
- configure chunker and max tokens
- display processing state
- show document summary
- inspect Markdown, Text, Structure, Chunks, and Metadata
- copy chunk content
- toggle raw vs contextualized chunk content

Recommended layout:

```text
frontend/
├── src/
│   ├── components/
│   ├── pages/
│   ├── services/
│   ├── hooks/
│   └── types/
└── package.json
```

### Flask API

The API exposes upload, document inspection, chunk inspection, deletion, and health endpoints.

Routes should not contain parser-specific logic. They call services and map domain errors to HTTP responses.

### DocumentService

Coordinates the processing workflow:

1. validate upload
2. persist original file
3. create/update document status
4. call parser
5. call serializer
6. call chunker
7. save artifacts, chunks, metrics, and errors

### ParserFactory

Maps extensions to parser implementations:

| Extension | Parser |
|---|---|
| `.pdf` | `DoclingParser` |
| `.docx` | `DoclingParser` |
| `.md` | `DoclingParser` |
| `.xlsx` | `DoclingParser` |
| `.xls` | `DoclingParser`, if runtime support exists |
| `.csv` | `DoclingParser` |
| `.txt` | `TextParser` |

### DoclingParser

Uses a shared `DoclingService` that owns a startup-initialized `DocumentConverter`.

PDF defaults:

```text
OCR enabled
force OCR disabled
table structure enabled
table mode accurate
```

The parser returns a `ParsedDocument` whose `structured_document` is the `DoclingDocument`.

### TextParser

Reads UTF-8 text with native Python and wraps it in the internal `ParsedDocument` shape so downstream serialization and chunking stay consistent. Encoding detection can be added later.

### SerializationService

Produces derived inspection artifacts:

- `document.json`
- `document.md`
- `document.txt`

Normalization must be light:

- normalize line endings
- remove null characters
- remove trailing spaces
- optionally apply Unicode NFKC

Do not flatten headings, lists, tables, paragraphs, code blocks, captions, or table boundaries.

### ChunkingService

Chunks from structured content.

Default:

```json
{
  "chunker": "hybrid",
  "max_tokens": 512,
  "tokenizer": "sentence-transformers/all-MiniLM-L6-v2"
}
```

Each output chunk stores:

- raw content
- contextualized content
- token count when available
- heading metadata
- page provenance when available
- source item references when available

## Domain Models

### ParsedDocument

```python
@dataclass
class ParsedDocument:
    source_format: str
    structured_document: object
    markdown: str
    text: str
    metadata: dict
```

### DocumentChunk

```python
@dataclass
class DocumentChunk:
    id: str
    document_id: str
    index: int
    content: str
    contextualized_content: str
    token_count: int | None
    metadata: dict
```

## API Surface

### `GET /api/health`

Reports API and Docling readiness.

### `POST /api/documents`

Accepts `multipart/form-data`:

```text
file
chunker
max_tokens
```

MVP may process synchronously and return a completed or failed document summary.

### `GET /api/documents/:id`

Returns metadata, status, processing counts, and metrics summary.

### `GET /api/documents/:id/content`

Returns Markdown/Text exports and available export types.

### `GET /api/documents/:id/structure`

Returns a sanitized structure summary. Full Docling JSON can be exposed later as a debug/download endpoint.

### `GET /api/documents/:id/chunks`

Returns ordered chunks with metadata.

### `DELETE /api/documents/:id`

Deletes database rows and filesystem artifacts.

## Persistence

Use SQLite for metadata and chunks, and local storage for large artifacts.

```text
storage/documents/{document_id}/
├── original.{ext}
├── document.json
├── document.md
├── document.txt
└── chunks.json
```

### `documents`

```text
id
filename
content_type
extension
size
status
page_count
table_count
picture_count
markdown_character_count
chunk_count
ocr_used
metadata_json
error_code
error_message
created_at
updated_at
```

### `chunks`

```text
id
document_id
chunk_index
content
contextualized_content
token_count
metadata_json
created_at
```

Index:

```text
(document_id, chunk_index)
```

## Errors

Standard response shape:

```json
{
  "error": {
    "code": "UNSUPPORTED_FILE_TYPE",
    "message": "This file type is not supported."
  }
}
```

Expected error codes:

```text
INVALID_FILE
UNSUPPORTED_FILE_TYPE
FILE_TOO_LARGE
EMPTY_FILE
DOCLING_INITIALIZATION_FAILED
DOCUMENT_CONVERSION_FAILED
EMPTY_EXTRACTION
OCR_FAILED
XLS_RUNTIME_UNAVAILABLE
SERIALIZATION_FAILED
CHUNKING_FAILED
PROCESSING_TIMEOUT
DOCUMENT_NOT_FOUND
```

## Security And Limits

Default limits:

```env
MAX_UPLOAD_SIZE_MB=20
MAX_DOCUMENT_PAGES=200
DOCUMENT_PROCESSING_TIMEOUT_SECONDS=120
```

Required safeguards:

- extension allow-list
- MIME validation where practical
- generated storage paths
- sanitized display names
- path traversal prevention
- empty-file rejection
- processing timeout
- safe logging

Uploaded content must never be executed.

## Configuration

Example:

```env
FLASK_ENV=development

MAX_UPLOAD_SIZE_MB=20
MAX_DOCUMENT_PAGES=200
DOCUMENT_PROCESSING_TIMEOUT_SECONDS=120

DOCLING_OCR_ENABLED=true
DOCLING_FORCE_OCR=false
DOCLING_TABLE_STRUCTURE_ENABLED=true
DOCLING_TABLE_MODE=accurate

DEFAULT_CHUNKER=hybrid
DEFAULT_CHUNK_MAX_TOKENS=512
DEFAULT_CHUNK_TOKENIZER=sentence-transformers/all-MiniLM-L6-v2

ENABLE_LEGACY_XLS=true

STORAGE_PATH=./storage/documents
DATABASE_URL=sqlite:///app.db
```

## Future Architecture

Keep the MVP synchronous until operational pressure justifies a split.

Likely evolution:

```text
React
  -> Flask API
  -> Queue
  -> Worker
  -> Docling
  -> Chunking
  -> Embedding
  -> Vector storage
```

Future storage path:

```text
SQLite
  -> PostgreSQL
  -> PostgreSQL + pgvector
```

Potential vector stores:

- PostgreSQL + pgvector
- Qdrant
- Chroma
- Elasticsearch
- OpenSearch
