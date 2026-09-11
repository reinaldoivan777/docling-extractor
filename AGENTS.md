# AGENTS.md

Guidance for agents and contributors working on the Document RAG Processor codebase.

## Project Intent

This project is a simple web application for document ingestion and RAG-ready chunking using Docling as the document understanding layer.

The MVP must let a user upload a supported document, convert it into a structured representation, serialize it for inspection, chunk it with structure-aware metadata, and inspect the results in a React UI.

Keep the MVP deliberately small:

- React + TypeScript frontend
- Python Flask backend
- Docling in-process inside Flask
- SQLite metadata storage
- Local filesystem document artifacts
- Synchronous processing

Do not add embedding, vector search, auth, queues, object storage, or chat unless explicitly requested.

## Core Principles

1. Preserve document structure as long as possible.
2. Treat `DoclingDocument` as the canonical representation for Docling-supported files.
3. Chunk from structured documents, not from flattened plain text, unless using a fallback path.
4. Keep parser logic out of Flask routes.
5. Store enough metadata for future retrieval and citation.
6. Keep file validation and storage safety strict.
7. Pin Docling and other processing dependencies once implementation begins.

## Required Pipeline

```text
Upload
  -> Validation
  -> Parser selection
  -> Conversion
  -> Structured document
  -> Serialization
  -> Structure-aware chunking
  -> Persistence
  -> UI inspection
```

## Supported MVP Formats

Allow only these extensions:

```text
.pdf
.docx
.txt
.md
.xlsx
.xls
.csv
```

Use Docling for:

- PDF
- DOCX
- Markdown
- XLSX
- XLS, only when LibreOffice/runtime support is available
- CSV

Use native Python for:

- TXT

If `.xls` support is enabled and LibreOffice is unavailable, return `XLS_RUNTIME_UNAVAILABLE`.

## Backend Boundaries

Recommended backend layout:

```text
backend/
├── app/
│   ├── routes/
│   ├── services/
│   ├── parsers/
│   ├── models/
│   ├── repositories/
│   ├── utils/
│   └── config.py
├── storage/
├── tests/
├── requirements.txt
└── run.py
```

Routes should only handle HTTP concerns:

- request parsing
- response formatting
- status codes
- error mapping

Services should own orchestration:

- validation
- parser selection
- conversion
- serialization
- chunking
- persistence

Parsers should implement a common interface:

```python
class DocumentParser:
    def parse(self, file_path: str):
        ...
```

Expected parser implementations:

- `DoclingParser`
- `TextParser`

## Storage Contract

Use generated document IDs and never user filenames as storage paths.

Recommended artifact layout:

```text
storage/documents/{document_id}/
├── original.{ext}
├── document.json
├── document.md
├── document.txt
└── chunks.json
```

SQLite should track:

- document metadata and status
- processing metrics
- error code/message
- chunk rows and chunk ordering

## API Contract

Required endpoints:

```text
GET    /api/health
POST   /api/documents
GET    /api/documents/:id
GET    /api/documents/:id/content
GET    /api/documents/:id/structure
GET    /api/documents/:id/chunks
DELETE /api/documents/:id
```

Use stable error envelopes:

```json
{
  "error": {
    "code": "DOCUMENT_CONVERSION_FAILED",
    "message": "Unable to process document."
  }
}
```

Never expose raw stack traces to the client.

## Chunk Contract

Every chunk must include:

```json
{
  "id": "chunk_uuid",
  "document_id": "document_uuid",
  "index": 0,
  "content": "...",
  "contextualized_content": "...",
  "token_count": 387,
  "metadata": {
    "filename": "report.pdf",
    "source_format": "pdf",
    "headings": [],
    "page_numbers": []
  }
}
```

Prefer Docling `HybridChunker` with token-based limits. `HierarchicalChunker` may be added as an option. Character chunking is only a fallback/debug strategy.

Default chunk settings:

```text
chunker=hybrid
max_tokens=512
tokenizer=sentence-transformers/all-MiniLM-L6-v2
```

## Security And Validation

Validate:

- file exists in request
- extension is allow-listed
- MIME type where practical
- file is not empty
- size is within `MAX_UPLOAD_SIZE_MB`
- page count/resource limits where practical
- selected parser can read the file

Always:

- generate storage filenames
- sanitize display filenames
- prevent path traversal
- delete temporary files
- set processing timeouts
- log errors without full document content

## Frontend Expectations

Build the actual document processing UI as the first screen.

Required views:

- upload area with drag/drop and file picker
- parser/chunking configuration
- processing status
- document summary
- tabs for Markdown, Text, Structure, Chunks, and Metadata
- chunk cards with token count, headings/pages when available, copy action, and raw/contextualized toggle

Keep the UI practical and inspection-focused. This is a developer/AI-engineer tool, not a marketing page.

## Testing Expectations

Add unit tests for:

- file validation
- parser factory
- text parser
- serialization service
- chunking service
- metadata mapping
- repository behavior

Add integration tests for:

- Flask upload to processing pipeline
- SQLite persistence
- Docling conversion
- DoclingDocument to HybridChunker

Use fixtures for:

- PDF
- scanned PDF
- PDF with table
- DOCX
- TXT
- Markdown
- XLSX
- CSV
- XLS if enabled

## Non-Goals For MVP

Do not implement unless specifically requested:

- LLM chat
- embedding generation
- vector database
- semantic search
- authentication
- multi-user workspaces
- cloud object storage
- distributed workers
- advanced document editor
- full layout viewer

## Dependency Notes

Docling APIs and supported formats can change. Pin package versions and verify against the pinned version before relying on API examples from documentation.

Primary references:

- https://docling-project.github.io/docling/usage/supported_formats/
- https://docling-project.github.io/docling/reference/cli/
- https://github.com/docling-project/docling
