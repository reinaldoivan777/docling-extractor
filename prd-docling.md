# PRD — Document Ingestion & RAG Chunking App with Docling

## 1. Product Overview

### Product Name
**Document RAG Processor — Docling Edition**

### Summary
Aplikasi web sederhana untuk mengunggah dokumen, memproses dan mengekstrak struktur dokumen menggunakan **Docling**, melakukan normalisasi ringan, lalu membagi dokumen menjadi chunks yang siap digunakan untuk proses Retrieval-Augmented Generation (RAG).

Berbeda dengan pendekatan parser yang hanya berfokus pada plain text, Docling digunakan sebagai **document understanding layer** yang menghasilkan representasi dokumen terstruktur (`DoclingDocument`). Struktur seperti heading, paragraph, list, table, page provenance, dan metadata sebisa mungkin dipertahankan sebelum proses chunking.

Aplikasi MVP mendukung:

- PDF
- DOCX
- TXT
- Markdown (`.md`)
- Excel (`.xlsx`)
- Excel legacy (`.xls`) dengan dependency tambahan
- CSV

Tech stack utama:

- **Frontend:** React + TypeScript
- **Backend:** Python Flask
- **Document Processing:** Docling
- **Document Representation:** DoclingDocument
- **RAG Chunking:** Docling HybridChunker / HierarchicalChunker
- **TXT fallback:** Native Python
- **Storage MVP:** Local filesystem + SQLite
- **Future Vector Storage:** PostgreSQL + pgvector, Qdrant, Chroma, Elasticsearch, atau OpenSearch

---

## 2. Problem Statement

Dokumen dari berbagai format memiliki struktur yang berbeda dan tidak selalu dapat direpresentasikan dengan baik sebagai plain text.

Contoh masalah:

- PDF dapat memiliki reading order yang kompleks.
- PDF hasil scan membutuhkan OCR.
- PDF dapat memiliki tabel, multi-column layout, gambar, formula, dan caption.
- DOCX memiliki heading, paragraph, list, table, header, dan footer.
- Excel memiliki workbook, sheet, row, column, dan cell.
- CSV bersifat tabular.
- TXT tidak memiliki struktur eksplisit.
- Markdown memiliki struktur heading yang penting untuk retrieval.
- Plain-text extraction dapat kehilangan informasi halaman dan hubungan antar elemen.
- Chunking berbasis karakter dapat memotong konteks semantik atau hierarchy dokumen.

Untuk pipeline RAG, aplikasi membutuhkan proses:

```text
Upload
  ↓
Validation
  ↓
Document Conversion
  ↓
Structured Document
  ↓
Normalization / Serialization
  ↓
Structure-aware Chunking
  ↓
RAG-ready chunks
```

Aplikasi ini menyediakan satu pipeline standar dengan Docling sebagai parser utama untuk format yang didukung.

---

## 3. Goals

### Primary Goals

1. User dapat mengunggah file dari browser.
2. Backend dapat memvalidasi tipe dan ukuran file.
3. Docling dapat mengubah file menjadi `DoclingDocument`.
4. Struktur dokumen sebisa mungkin dipertahankan.
5. Sistem dapat menghasilkan Markdown/Text untuk inspection.
6. Sistem dapat melakukan structure-aware chunking.
7. User dapat melihat hasil extraction, Markdown, metadata, dan chunks.
8. Pipeline memiliki status yang jelas:
   - uploaded
   - converting
   - normalizing
   - chunking
   - completed
   - failed
9. Output chunk memiliki metadata yang cukup untuk retrieval dan citation.
10. Parser layer tidak tightly coupled dengan route/API Flask.

### Secondary Goals

- Menjadi fondasi untuk embedding dan vector search.
- Mendukung OCR untuk scanned PDF.
- Mempertahankan table structure lebih baik.
- Mendukung page-aware dan heading-aware metadata.
- Memiliki logging dan error handling.
- Memungkinkan pemilihan chunking strategy.
- Memungkinkan konfigurasi tokenizer dan maximum tokens.
- Memudahkan migrasi dari synchronous processing ke background worker.

---

## 4. Non-Goals — MVP

MVP belum mencakup:

- LLM chat interface
- Embedding generation
- Semantic search
- Vector database
- Authentication
- Multi-user workspace
- Cloud object storage
- Agentic RAG
- Fine-tuning
- Image understanding dengan VLM sebagai default
- Advanced formula understanding
- Production-grade distributed worker
- Complex document versioning
- Human document editor
- Full layout viewer

OCR dasar melalui Docling dapat digunakan, tetapi advanced OCR tuning bukan fokus utama MVP.

---

# 5. Target Users

## Primary User

Developer atau AI engineer yang ingin:

- menguji kualitas document ingestion;
- menyiapkan dokumen untuk RAG;
- melihat struktur dokumen setelah conversion;
- membandingkan text/Markdown extraction;
- melihat chunk boundaries;
- memeriksa metadata chunk;
- mengetahui page/section asal suatu chunk.

## Example User Journey

User memiliki:

```text
annual-report.pdf
```

User ingin:

```text
upload
→ convert with Docling
→ inspect structured document
→ export Markdown
→ chunk
→ inspect metadata
```

sebelum memasukkan chunks ke embedding model dan vector database.

---

# 6. Supported File Types

| File Type | Extension | Parser Strategy | Notes |
|---|---|---|---|
| PDF | `.pdf` | Docling | OCR + table extraction configurable |
| Word | `.docx` | Docling | Native structured conversion |
| Text | `.txt` | Native Python | Wrapped into internal parsed document |
| Markdown | `.md` | Docling | Preserve heading hierarchy |
| Excel | `.xlsx` | Docling | Structured spreadsheet conversion |
| Excel Legacy | `.xls` | Docling + LibreOffice | Requires additional runtime dependency |
| CSV | `.csv` | Docling | Tabular document |

MVP harus memiliki allow-list eksplisit walaupun Docling mendukung format lain.

Future formats dapat mencakup:

```text
PPTX
HTML
Images
EPUB
RTF
ODT / ODS / ODP
```

---

# 7. Product Flow

```text
┌──────────────┐
│ React Client │
└──────┬───────┘
       │ multipart/form-data
       ▼
┌──────────────┐
│ Flask API    │
└──────┬───────┘
       │
       ├── Validate File
       ├── Save Temporary File
       ▼
┌───────────────────────┐
│ DocumentParserFactory │
└───────────┬───────────┘
            │
     ┌──────┴────────┐
     ▼               ▼
┌──────────────┐ ┌──────────────┐
│ Docling      │ │ Native TXT   │
│ Converter    │ │ Parser       │
└──────┬───────┘ └──────┬───────┘
       │                 │
       └────────┬────────┘
                ▼
       ┌─────────────────┐
       │ Parsed Document │
       │ + Structure     │
       │ + Metadata      │
       └────────┬────────┘
                ▼
       ┌─────────────────┐
       │ Serializer /    │
       │ Normalizer      │
       └────────┬────────┘
                ▼
       ┌─────────────────┐
       │ Docling Chunker │
       └────────┬────────┘
                ▼
       ┌─────────────────┐
       │ RAG-ready       │
       │ chunks          │
       └─────────────────┘
```

---

# 8. Functional Requirements

## FR-01 — Upload Document

User dapat mengunggah satu dokumen.

### Accepted Formats

```text
.pdf
.docx
.txt
.md
.xlsx
.xls
.csv
```

### Requirements

Backend harus memvalidasi:

- file tersedia;
- extension diperbolehkan;
- MIME type;
- file tidak kosong;
- ukuran file tidak melebihi limit;
- filename tidak digunakan langsung sebagai storage path;
- file dapat dibaca oleh parser yang dipilih.

### MVP File Size Limit

Default:

```text
20 MB
```

Configurable:

```env
MAX_UPLOAD_SIZE_MB=20
```

### User Interface

Upload area memiliki:

- drag and drop;
- file picker;
- supported formats;
- maximum file size;
- selected filename;
- file size;
- parser configuration;
- chunking configuration;
- process button.

---

# 9. Document Status

Setiap dokumen memiliki status:

```text
UPLOADED
CONVERTING
NORMALIZING
CHUNKING
COMPLETED
FAILED
```

Flow:

```text
UPLOADED
   ↓
CONVERTING
   ↓
NORMALIZING
   ↓
CHUNKING
   ↓
COMPLETED
```

Failure dapat terjadi pada setiap stage.

Optional future statuses:

```text
QUEUED
OCR_PROCESSING
EMBEDDING
INDEXING
```

---

# 10. Docling Integration

## Architecture Decision

Untuk MVP, **Docling berjalan di process Python yang sama dengan Flask backend**.

```text
Flask API
   │
   │ Python call
   ▼
Docling DocumentConverter
```

Docling tidak wajib dijalankan sebagai service terpisah.

Alasan:

- Docling merupakan Python library.
- Mengurangi network hop.
- Deployment MVP lebih sederhana.
- Tidak membutuhkan dedicated parser HTTP container.
- `DocumentConverter` dapat digunakan langsung dari application service.
- Lebih mudah mengakses `DoclingDocument` dan metadata terstruktur.

Future deployment boleh menggunakan **docling-serve** sebagai service terpisah apabila:

- processing perlu diskalakan independen;
- model inference menggunakan GPU worker;
- API instances tidak boleh memuat model;
- workload conversion berat;
- dibutuhkan horizontal scaling khusus ingestion.

## Responsibilities

Docling digunakan untuk:

- document conversion;
- layout-aware PDF processing;
- OCR pada bitmap/scanned content;
- table structure extraction;
- DOCX processing;
- Markdown processing;
- XLSX/CSV processing;
- metadata extraction;
- export ke Markdown;
- export ke plain text;
- lossless structured JSON melalui `DoclingDocument`;
- hierarchy-aware document traversal;
- RAG-aware chunking.

---

# 11. Docling Output Model

Primary internal representation:

```text
DoclingDocument
```

Application tidak boleh langsung membuang struktur menjadi plain text pada awal pipeline.

Internal processing:

```text
source file
   ↓
DoclingDocument
   ├── texts
   ├── headings
   ├── lists
   ├── tables
   ├── pictures
   ├── hierarchy
   └── provenance
```

Untuk UI/debugging, sistem dapat mengekspor:

```text
Markdown
Plain Text
Docling JSON
```

Recommended persisted outputs:

```text
original file
document.json
document.md
chunks.json
```

Plain text bersifat optional.

---

# 12. File-Specific Parsing Strategy

## PDF

Primary parser:

```text
Docling
```

Pipeline:

```text
PDF
 ↓
Docling PDF Pipeline
 ↓
Layout Analysis
 ↓
OCR when required
 ↓
Table Structure
 ↓
DoclingDocument
 ↓
Chunking
```

### Default PDF Configuration

Recommended MVP:

```text
OCR: enabled
force OCR: disabled
table structure: enabled
table mode: accurate
```

Tujuan:

- text-based PDF tetap menggunakan text layer bila tersedia;
- scanned regions dapat diproses OCR;
- table structure tetap dipertahankan;
- tidak memaksa OCR seluruh halaman tanpa kebutuhan.

### Scanned PDF

Berbeda dari versi parser sebelumnya, scanned PDF tidak langsung dianggap gagal.

Expected behavior:

```text
PDF scan
 ↓
Docling OCR
 ↓
structured extraction
```

Jika OCR tetap gagal atau tidak menghasilkan konten yang bermakna:

```text
error_code = EMPTY_EXTRACTION
```

atau:

```text
error_code = OCR_FAILED
```

---

## DOCX

Primary parser:

```text
Docling
```

Target extraction:

- heading hierarchy;
- paragraphs;
- lists;
- tables;
- document order;
- metadata where available.

Chunking harus memanfaatkan heading/section context bila tersedia.

---

## TXT

Docling bukan parser utama untuk plain `.txt`.

Gunakan native Python:

```python
path.read_text(encoding="utf-8")
```

Fallback encoding detection dapat ditambahkan.

TXT kemudian dikonversi ke internal application model agar pipeline selanjutnya tetap konsisten.

```text
TXT
 ↓
Native Parser
 ↓
ParsedDocument
 ↓
Normalize
 ↓
Chunk
```

---

## Markdown

Primary parser:

```text
Docling
```

Markdown structure harus dipertahankan:

```md
# Heading

## Subheading

- item
- item
```

Heading dapat menjadi bagian dari contextual metadata chunk.

---

## Excel XLSX

Primary parser:

```text
Docling
```

Target:

- workbook content;
- sheet context;
- tables;
- cell values;
- row/column structure bila tersedia pada representation.

UI dapat menampilkan Markdown serialization untuk inspection, tetapi internal structured representation tetap menjadi source of truth.

---

## Excel XLS

Primary strategy:

```text
Docling
+
LibreOffice runtime dependency
```

Karena format legacy membutuhkan conversion support tambahan, deployment harus memastikan LibreOffice tersedia apabila `.xls` diaktifkan.

Jika LibreOffice tidak tersedia:

```text
XLS_RUNTIME_UNAVAILABLE
```

Alternatif MVP yang lebih sederhana:

```text
disable .xls
support .xlsx only
```

---

## CSV

Primary parser:

```text
Docling
```

CSV diperlakukan sebagai tabular document.

Chunking sebaiknya menghindari pemotongan row secara arbitrer.

Future option:

```text
row-group chunking
```

---

# 13. Normalization Strategy

Karena Docling sudah menghasilkan structured document, normalisasi tidak boleh agresif.

Tujuan normalization adalah membersihkan hasil serialization tanpa merusak hierarchy.

## Rules

### Normalize line endings

Convert:

```text
\r\n
\r
```

to:

```text
\n
```

### Remove null characters

Remove:

```text
\x00
```

### Remove trailing spaces

Trailing whitespace boleh dihapus.

### Unicode normalization

Optional:

```python
unicodedata.normalize("NFKC", text)
```

Harus configurable.

### Preserve Structure

Jangan meratakan:

- headings;
- lists;
- table boundaries;
- paragraph boundaries;
- code blocks;
- captions.

### Important Principle

```text
DoclingDocument
```

adalah canonical representation.

Normalized Markdown/Text hanya derived representation.

---

# 14. Serialization Output

Sistem menyimpan minimal:

```json
{
  "markdown": "...",
  "text": "...",
  "docling_json_path": "..."
}
```

Recommended filesystem:

```text
storage/documents/{document_id}/
├── original.pdf
├── document.json
├── document.md
├── document.txt
└── chunks.json
```

---

# 15. Chunking

## MVP Strategy

Gunakan Docling chunking built-in.

Primary:

```text
HybridChunker
```

Alternative:

```text
HierarchicalChunker
```

### Why HybridChunker

Hybrid chunking dipilih karena:

- memanfaatkan hierarchy document;
- dapat menggunakan tokenizer;
- lebih cocok untuk embedding/RAG daripada character-only split;
- dapat menambahkan contextualized metadata seperti heading;
- mengurangi kemungkinan chunk terpotong di boundary yang buruk.

Pipeline:

```text
DoclingDocument
       ↓
HybridChunker
       ↓
DocChunk
       ↓
contextualize()
       ↓
RAG-ready chunk
```

---

# 16. Chunk Configuration

Default MVP:

```json
{
  "chunker": "hybrid",
  "max_tokens": 512,
  "tokenizer": "sentence-transformers/all-MiniLM-L6-v2"
}
```

Environment:

```env
DEFAULT_CHUNKER=hybrid
DEFAULT_CHUNK_MAX_TOKENS=512
DEFAULT_CHUNK_TOKENIZER=sentence-transformers/all-MiniLM-L6-v2
```

Optional request configuration:

```json
{
  "chunker": "hybrid",
  "max_tokens": 512
}
```

MVP tidak menggunakan `chunk_size=1000 characters` sebagai strategi utama.

Character-based chunker dapat dipertahankan hanya sebagai fallback/debug strategy.

---

# 17. Chunk Object

Setiap chunk minimal memiliki:

```json
{
  "id": "chunk_uuid",
  "document_id": "document_uuid",
  "index": 0,
  "content": "...",
  "token_count": 387,
  "metadata": {
    "filename": "report.pdf",
    "headings": [
      "Financial Performance",
      "Revenue"
    ],
    "page_numbers": [4]
  }
}
```

Recommended metadata:

```json
{
  "content_type": "application/pdf",
  "source_format": "pdf",
  "headings": [],
  "page_numbers": [],
  "captions": [],
  "section": null,
  "table_refs": [],
  "source_items": []
}
```

Jika metadata tidak tersedia dari source format, field boleh kosong.

---

# 18. Chunk Contextualization

Sebelum embedding, chunk content dapat dibuat contextualized.

Concept:

```text
Heading: Financial Performance
Subheading: Revenue

Revenue increased by ...
```

Simpan dua versi:

```json
{
  "raw_content": "...",
  "contextualized_content": "..."
}
```

Untuk embedding direkomendasikan menggunakan:

```text
contextualized_content
```

sedangkan source display dapat tetap memakai raw content.

---

# 19. Upload API

## POST `/api/documents`

### Request

```text
multipart/form-data
```

Fields:

```text
file
chunker
max_tokens
```

Example:

```bash
curl -X POST http://localhost:5000/api/documents \
  -F "file=@report.pdf" \
  -F "chunker=hybrid" \
  -F "max_tokens=512"
```

### Response

```json
{
  "id": "doc_123",
  "filename": "report.pdf",
  "content_type": "application/pdf",
  "size": 1048576,
  "status": "COMPLETED",
  "chunk_count": 24
}
```

MVP boleh synchronous.

Untuk dokumen besar, API harus memiliki configurable processing timeout.

---

# 20. Get Document API

## GET `/api/documents/:id`

Response:

```json
{
  "id": "doc_123",
  "filename": "report.pdf",
  "content_type": "application/pdf",
  "size": 1048576,
  "status": "COMPLETED",
  "created_at": "2026-09-11T10:00:00Z",
  "processing": {
    "page_count": 20,
    "markdown_character_count": 23100,
    "chunk_count": 24,
    "ocr_used": false,
    "table_count": 7
  }
}
```

---

# 21. Get Document Content API

## GET `/api/documents/:id/content`

Response:

```json
{
  "document_id": "doc_123",
  "markdown": "...",
  "text": "...",
  "available_exports": [
    "markdown",
    "text",
    "json"
  ]
}
```

---

# 22. Get Structured Document API

## GET `/api/documents/:id/structure`

MVP dapat mengembalikan sanitized representation.

```json
{
  "document_id": "doc_123",
  "pages": 20,
  "tables": 7,
  "pictures": 3,
  "headings": [
    "Executive Summary",
    "Financial Performance"
  ]
}
```

Full Docling JSON sebaiknya tersedia melalui download/debug endpoint jika ukurannya besar.

---

# 23. Get Chunks API

## GET `/api/documents/:id/chunks`

Response:

```json
{
  "document_id": "doc_123",
  "count": 2,
  "chunks": [
    {
      "id": "chunk_1",
      "index": 0,
      "content": "...",
      "contextualized_content": "...",
      "token_count": 488,
      "metadata": {
        "headings": ["Executive Summary"],
        "page_numbers": [1]
      }
    }
  ]
}
```

---

# 24. Delete Document API

## DELETE `/api/documents/:id`

Deletes:

- original uploaded file;
- Docling JSON;
- Markdown;
- text export;
- chunks;
- metadata.

Response:

```json
{
  "success": true
}
```

---

# 25. Health Check

## GET `/api/health`

Karena Docling in-process, health check tidak melakukan HTTP ping ke parser service.

Response:

```json
{
  "status": "ok",
  "services": {
    "api": "healthy",
    "docling": "ready"
  }
}
```

Optional readiness information:

```json
{
  "docling": {
    "ready": true,
    "ocr_enabled": true,
    "xls_support": true
  }
}
```

Jika model/dependency initialization gagal:

```json
{
  "status": "degraded",
  "services": {
    "api": "healthy",
    "docling": "initialization_failed"
  }
}
```

---

# 26. Frontend Requirements

## Main Page

```text
┌──────────────────────────────────────┐
│ Document RAG Processor               │
│                                      │
│ ┌──────────────────────────────────┐ │
│ │ Drag document here               │ │
│ │                                  │ │
│ │ PDF DOCX TXT MD XLSX XLS CSV     │ │
│ └──────────────────────────────────┘ │
│                                      │
│ Chunker:    [Hybrid ▼]               │
│ Max Tokens: [512]                    │
│                                      │
│ PDF OCR:    [Auto ▼]                 │
│                                      │
│              [ Process ]             │
└──────────────────────────────────────┘
```

---

# 27. Processing UI

Display stages:

```text
✓ Upload
✓ Conversion
✓ Serialization
→ Chunking
```

Jika OCR digunakan:

```text
✓ Upload
→ OCR + Document Conversion
○ Serialization
○ Chunking
```

MVP boleh hanya menampilkan:

```text
Processing document...
```

---

# 28. Result Page

Example:

```text
report.pdf

Status: Completed
Type: application/pdf
Size: 1.2 MB
Pages: 20
Tables: 7
Chunks: 24
OCR: Not required
```

Tabs:

```text
[ Markdown ] [ Text ] [ Structure ] [ Chunks ] [ Metadata ]
```

---

# 29. Markdown Tab

Menampilkan:

```text
document.export_to_markdown()
```

Gunakan:

```text
monospace / pre-wrap
```

Optional:

- raw Markdown view;
- rendered Markdown view.

---

# 30. Text Tab

Menampilkan plain text export.

Tujuan:

- debugging;
- comparison;
- compatibility testing;
- melihat apakah structure-to-text serialization menghasilkan output masuk akal.

---

# 31. Structure Tab

Menampilkan summary dari `DoclingDocument`.

Example:

```text
Pages      20
Headings   34
Tables      7
Pictures    3
```

Optional tree:

```text
Financial Report
├── Executive Summary
├── Business Overview
└── Financial Performance
    ├── Revenue
    └── Operating Costs
```

---

# 32. Chunks Tab

Display:

```text
Chunk #1
Tokens: 488
Pages: 1
Section: Executive Summary

...
```

Setiap chunk memiliki:

- chunk index;
- token count;
- source page;
- headings;
- copy button;
- expandable content;
- raw/contextualized toggle.

---

# 33. Metadata Tab

Example:

```json
{
  "filename": "report.pdf",
  "source_format": "pdf",
  "page_count": 20,
  "table_count": 7,
  "picture_count": 3,
  "ocr_used": false
}
```

Metadata berbeda tergantung source.

---

# 34. Backend Architecture

Recommended Flask structure:

```text
backend/
├── app/
│   ├── __init__.py
│   │
│   ├── routes/
│   │   ├── documents.py
│   │   └── health.py
│   │
│   ├── services/
│   │   ├── document_service.py
│   │   ├── docling_service.py
│   │   ├── serialization_service.py
│   │   └── chunking_service.py
│   │
│   ├── parsers/
│   │   ├── base.py
│   │   ├── docling_parser.py
│   │   └── text_parser.py
│   │
│   ├── models/
│   │   ├── document.py
│   │   └── chunk.py
│   │
│   ├── repositories/
│   │   └── document_repository.py
│   │
│   ├── utils/
│   │   ├── file.py
│   │   └── errors.py
│   │
│   └── config.py
│
├── storage/
│   └── documents/
│
├── tests/
├── requirements.txt
└── run.py
```

---

# 35. Frontend Architecture

```text
frontend/
├── src/
│   ├── components/
│   │   ├── FileUpload.tsx
│   │   ├── ProcessingStatus.tsx
│   │   ├── DocumentSummary.tsx
│   │   ├── MarkdownViewer.tsx
│   │   ├── StructureViewer.tsx
│   │   ├── ChunkCard.tsx
│   │   └── MetadataViewer.tsx
│   │
│   ├── pages/
│   │   ├── UploadPage.tsx
│   │   └── DocumentPage.tsx
│   │
│   ├── services/
│   │   └── documentApi.ts
│   │
│   ├── hooks/
│   │   └── useDocument.ts
│   │
│   └── types/
│       └── document.ts
│
└── package.json
```

---

# 36. Parser Abstraction

Jangan coupling `DocumentService` langsung ke Docling.

```python
from abc import ABC, abstractmethod

class DocumentParser(ABC):

    @abstractmethod
    def parse(self, file_path: str):
        ...
```

Implementations:

```text
DoclingParser
TextParser
```

Selection:

```text
PDF     → DoclingParser
DOCX    → DoclingParser
MD      → DoclingParser
XLSX    → DoclingParser
XLS     → DoclingParser
CSV     → DoclingParser
TXT     → TextParser
```

Tujuan:

- mudah mengganti parser;
- mudah melakukan A/B comparison;
- memungkinkan parser fallback;
- memungkinkan future `DoclingServeParser`.

---

# 37. Docling Service

Concept:

```python
from docling.document_converter import DocumentConverter

class DoclingService:

    def __init__(self, converter: DocumentConverter):
        self.converter = converter

    def convert(self, file_path: str):
        result = self.converter.convert(file_path)
        return result.document
```

`DocumentConverter` sebaiknya diinisialisasi sekali ketika application startup, bukan dibuat ulang setiap request.

Benefits:

- menghindari repeated model initialization;
- mengurangi overhead;
- memudahkan configuration;
- memudahkan dependency injection dan testing.

---

# 38. PDF Pipeline Configuration

Pseudo configuration:

```python
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

pdf_options = PdfPipelineOptions()
pdf_options.do_ocr = True
pdf_options.do_table_structure = True

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(
            pipeline_options=pdf_options
        )
    }
)
```

Exact options dapat berubah antar versi Docling; pin package version di project.

Recommended:

```text
docling==<pinned-version>
```

Jangan menggunakan unpinned `latest` untuk production.

---

# 39. Processing Pipeline

Recommended orchestration:

```python
def process_document(document):

    parser = parser_factory.get(document.extension)

    parsed = parser.parse(document.file_path)

    serialization = serializer.serialize(parsed)

    chunks = chunking_service.chunk(parsed)

    repository.save_result(
        document=document,
        markdown=serialization.markdown,
        text=serialization.text,
        structured_document=serialization.json,
        chunks=chunks,
        metadata=parsed.metadata,
    )
```

Critical principle:

```text
Chunk from structured document
```

bukan:

```text
Docling
→ plain text
→ generic splitter
```

kecuali fallback diperlukan.

---

# 40. Internal Domain Model

## ParsedDocument

```python
@dataclass
class ParsedDocument:
    source_format: str
    structured_document: object
    markdown: str
    text: str
    metadata: dict
```

Untuk DoclingParser:

```text
structured_document = DoclingDocument
```

Untuk TextParser:

```text
structured_document = internal lightweight document
```

## DocumentChunk

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

---

# 41. Storage — MVP

Use:

```text
SQLite
+
local filesystem
```

Structure:

```text
storage/documents/{document_id}/
├── original.{ext}
├── document.json
├── document.md
├── document.txt
└── chunks.json
```

SQLite tables:

```text
documents
chunks
```

---

# 42. Document Table

```text
documents
---------
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

---

# 43. Chunk Table

```text
chunks
------
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

---

# 44. Error Handling

Standard:

```json
{
  "error": {
    "code": "DOCUMENT_CONVERSION_FAILED",
    "message": "Unable to process document."
  }
}
```

Suggested codes:

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

Jangan expose raw stack trace ke client.

---

# 45. Validation & Security

Required:

- whitelist extensions;
- validate MIME where practical;
- maximum upload size;
- generated storage filename;
- sanitize display filename;
- prevent path traversal;
- delete temporary files;
- reject empty files;
- do not execute uploaded content;
- set processing timeout;
- limit supported formats explicitly;
- limit page count where necessary;
- log failure safely.

Example:

```text
storage/documents/
  3f5c9472-.../
    original.pdf
```

Never:

```text
storage/../../../etc/passwd
```

---

# 46. Resource Limits

Docling PDF processing dapat lebih berat daripada simple text parser.

Recommended configurable limits:

```env
MAX_UPLOAD_SIZE_MB=20
MAX_DOCUMENT_PAGES=200
DOCUMENT_PROCESSING_TIMEOUT_SECONDS=120
```

Optional future:

```env
MAX_CONCURRENT_CONVERSIONS=2
```

Production worker harus memiliki:

- memory limit;
- CPU limit;
- timeout;
- queue backpressure.

---

# 47. Configuration

Example `.env`:

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

---

# 48. Docker Development Setup

## Recommended MVP Containers

```text
frontend
backend
```

Architecture:

```text
Browser
  ↓
React :5173
  ↓
Flask :5000
  ↓
Docling Python Library
```

Example:

```yaml
services:

  backend:
    build: ./backend
    ports:
      - "5000:5000"
    volumes:
      - ./backend/storage:/app/storage

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend
```

Tidak ada dedicated Docling container untuk MVP.

Jika `.xls` digunakan, backend image perlu menyediakan LibreOffice runtime.

---

# 49. Optional Future: Docling Serve Architecture

Jika processing menjadi berat:

```text
React
  ↓
Flask API
  ↓
Queue
  ↓
Worker
  ↓
Docling
```

Alternative:

```text
Flask API
   ↓ HTTP
Docling Serve
```

Gunakan service split hanya ketika operational benefit sudah jelas.

Potential triggers:

- conversion throughput tinggi;
- multiple API replicas;
- GPU inference;
- independent autoscaling;
- long-running OCR jobs.

---

# 50. Logging

Events:

```text
document.uploaded
document.conversion.started
document.conversion.completed
document.ocr.used
document.serialization.started
document.serialization.completed
document.chunking.started
document.chunking.completed
document.processing.failed
```

Include:

```text
document_id
filename
content_type
source_format
page_count
duration_ms
ocr_used
table_count
chunk_count
error_code
```

Jangan log full document content.

---

# 51. Processing Metrics

Store:

```json
{
  "upload_size_bytes": 1048576,
  "page_count": 20,
  "table_count": 7,
  "picture_count": 3,
  "markdown_character_count": 23900,
  "chunk_count": 25,
  "ocr_used": false,
  "conversion_duration_ms": 2810,
  "serialization_duration_ms": 18,
  "chunking_duration_ms": 35,
  "total_duration_ms": 2863
}
```

Future operational metrics:

```text
documents_processed_total
documents_failed_total
conversion_duration_seconds
ocr_documents_total
chunk_count_histogram
processing_queue_depth
```

---

# 52. Acceptance Criteria — Upload

### AC-01

Given:

```text
valid PDF <= 20 MB
```

When user uploads document,

Then system returns:

```text
COMPLETED
```

dan menghasilkan Docling document + chunks.

### AC-02

Given:

```text
.exe
```

Then:

```text
UNSUPPORTED_FILE_TYPE
```

### AC-03

Given file exceeds limit:

```text
FILE_TOO_LARGE
```

---

# 53. Acceptance Criteria — Conversion

### AC-04

Given DOCX dengan heading dan paragraphs,

Then Markdown output mempertahankan logical order dan heading secara reasonable.

### AC-05

Given TXT UTF-8,

Then TextParser menghasilkan content dan chunks.

### AC-06

Given scanned PDF,

Then system mencoba OCR dan tidak otomatis mengembalikan `OCR_REQUIRED`.

### AC-07

Given PDF dengan tabel,

Then structured document memiliki table representation atau table content yang dapat diekspor.

### AC-08

Given XLSX dengan multiple sheets,

Then relevant sheet content tersedia pada converted representation.

### AC-09

Given legacy XLS tetapi LibreOffice tidak tersedia,

Then:

```text
XLS_RUNTIME_UNAVAILABLE
```

---

# 54. Acceptance Criteria — Serialization

### AC-10

Markdown export tersedia setelah successful Docling conversion.

### AC-11

Structured JSON disimpan untuk Docling-processed documents.

### AC-12

Paragraph dan heading tidak diratakan secara agresif.

### AC-13

Null characters tidak muncul pada normalized text export.

---

# 55. Acceptance Criteria — Chunking

### AC-14

Document yang memiliki content menghasilkan minimal satu chunk.

### AC-15

Chunk ordering mengikuti urutan source.

### AC-16

Chunk object memiliki:

```text
id
document_id
index
content
metadata
```

### AC-17

Hybrid chunking menghormati configured max token limit secara reasonable.

### AC-18

Jika heading tersedia, heading context dapat ditemukan pada chunk metadata atau contextualized content.

### AC-19

Jika page provenance tersedia, page number dapat ditelusuri dari chunk.

---

# 56. Testing Requirements

## Unit Tests

Required:

```text
file validation
parser_factory
text_parser
serialization_service
chunking_service
metadata mapper
repository
```

## Integration Tests

Required:

```text
Flask → Docling
Flask → SQLite
DoclingDocument → HybridChunker
```

Fixtures:

```text
sample.pdf
sample-scanned.pdf
sample-table.pdf
sample.docx
sample.txt
sample.md
sample.xlsx
sample.csv
```

Jika `.xls` enabled:

```text
sample.xls
```

---

# 57. Edge Cases

Test:

```text
empty PDF
scanned PDF
mixed text + scanned PDF
encrypted PDF
very large PDF
multi-column PDF
PDF with tables
PDF with images
empty TXT
UTF-8 TXT
non-UTF8 TXT
large DOCX
DOCX with nested tables
Excel multiple sheets
Excel merged cells
CSV quoted commas
CSV multiline values
Markdown code block
Markdown nested headings
very long section
document with no headings
```

---

# 58. MVP Success Metrics

MVP dianggap berhasil jika:

1. Semua enabled file format dapat diterima.
2. Text PDF dapat diproses.
3. Scanned PDF dapat dicoba melalui OCR.
4. DOCX dapat dikonversi menjadi structured document.
5. Markdown hierarchy dipertahankan.
6. XLSX/CSV menghasilkan useful structured representation.
7. TXT dapat diproses melalui native parser.
8. Docling JSON atau equivalent structured output tersimpan.
9. Markdown export dapat ditampilkan.
10. Chunks dapat dihasilkan langsung dari structured document.
11. Chunk memiliki useful metadata.
12. User dapat melihat Markdown/Text/Structure/Chunks/Metadata.
13. Conversion failure tidak menyebabkan Flask crash.
14. Processing metrics tercatat.
15. Parser dapat diganti tanpa mengubah route/API layer.

---

# 59. MVP Implementation Phases

## Phase 1 — Infrastructure

Implement:

```text
React
Flask
SQLite
Docling dependency
Docker
```

Deliverable:

```text
React → Flask → Docling local conversion
```

---

## Phase 2 — Upload

Implement:

```text
POST /api/documents
file validation
temporary/local storage
document metadata
```

---

## Phase 3 — Document Conversion

Implement:

```text
Parser abstraction
DoclingParser
TextParser
DocumentConverter configuration
PDF OCR configuration
table extraction
```

---

## Phase 4 — Serialization

Implement:

```text
Markdown export
Text export
Docling JSON persistence
metadata summary
```

---

## Phase 5 — Chunking

Implement:

```text
HybridChunker
HierarchicalChunker option
contextualized content
chunk metadata mapping
```

---

## Phase 6 — Result UI

Implement:

```text
Markdown
Text
Structure
Chunks
Metadata
```

---

## Phase 7 — Persistence

Implement:

```text
SQLite
documents
chunks
local storage
```

---

## Phase 8 — Testing

Add:

```text
unit tests
integration tests
sample fixtures
OCR fixture
table fixture
```

---

# 60. Future Phase — Embedding

Pipeline:

```text
DoclingDocument
      ↓
HybridChunker
      ↓
Contextualized Chunk
      ↓
Embedding Model
      ↓
Vector
      ↓
Vector Database
```

Chunk:

```json
{
  "id": "chunk_123",
  "document_id": "doc_123",
  "content": "...",
  "contextualized_content": "...",
  "embedding": [0.123, 0.543],
  "metadata": {
    "page_numbers": [4],
    "headings": ["Revenue"]
  }
}
```

Possible providers:

```text
OpenAI
Sentence Transformers
Ollama
HuggingFace
```

---

# 61. Future Phase — Vector Storage

Options:

```text
PostgreSQL + pgvector
Qdrant
Chroma
Elasticsearch
OpenSearch
```

Recommended evolution:

```text
SQLite
  ↓
PostgreSQL
  ↓
PostgreSQL + pgvector
```

---

# 62. Future Phase — Retrieval

Endpoint:

```text
POST /api/search
```

Request:

```json
{
  "query": "What was the company's revenue?",
  "top_k": 5
}
```

Pipeline:

```text
query
 ↓
embedding
 ↓
vector search
 ↓
top chunks
 ↓
metadata + page provenance
```

---

# 63. Future Phase — RAG

```text
User Question
      ↓
Query Embedding
      ↓
Hybrid / Vector Search
      ↓
Relevant Docling Chunks
      ↓
Optional Reranking
      ↓
Prompt Construction
      ↓
LLM
      ↓
Answer + Source Citation
```

Docling provenance metadata digunakan untuk future citations.

---

# 64. Future Improvements

Potential roadmap:

- background processing;
- Celery / RQ;
- Redis queue;
- MinIO / S3;
- PostgreSQL;
- pgvector;
- embeddings;
- semantic search;
- hybrid search;
- reranking;
- RAG chat;
- page citations;
- document citations;
- VLM pipeline;
- picture description;
- formula enrichment;
- code enrichment;
- async batch ingestion;
- URL ingestion;
- document versioning;
- deduplication;
- document comparison;
- chunk quality evaluation;
- retrieval evaluation;
- observability;
- docling-serve deployment.

---

# 65. Recommended MVP Boundary

Keep architecture simple:

```text
React
  ↓
Flask
  ↓
Parser Factory
  ├── DoclingParser
  └── TextParser
        ↓
Structured Document
        ↓
Serializer
        ↓
Docling HybridChunker
        ↓
SQLite + JSON
```

Processing synchronous:

```text
POST document
      ↓
validate
      ↓
convert
      ↓
serialize
      ↓
chunk
      ↓
persist
      ↓
response
```

Setelah pipeline stabil:

```text
POST document
      ↓
Queue
      ↓
Worker
      ↓
Docling
      ↓
Chunk
      ↓
Embed
      ↓
Index
```

---

# 66. Definition of Done — MVP

MVP selesai apabila user dapat:

```text
1. Open application
2. Select supported document
3. Upload document
4. Backend validates file
5. Docling / selected parser converts document
6. Structured representation is preserved
7. System exports Markdown/Text
8. System generates chunks
9. User sees document summary
10. User sees Markdown output
11. User sees structured document summary
12. User sees generated chunks
13. User can inspect chunk metadata
14. User can trace page/heading where available
15. Errors are displayed clearly
16. Processing does not crash Flask
```

Final MVP pipeline:

```text
                     ┌─────────────────┐
                     │      React      │
                     │                 │
                     │ Upload Document │
                     └────────┬────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │      Flask      │
                     │ File Validation │
                     └────────┬────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │ Parser Factory  │
                     └────────┬────────┘
                              │
                  ┌───────────┴───────────┐
                  ▼                       ▼
          ┌────────────────┐      ┌──────────────┐
          │ Docling Parser │      │ TXT Parser   │
          └───────┬────────┘      └──────┬───────┘
                  │                      │
                  └──────────┬───────────┘
                             ▼
                   ┌──────────────────┐
                   │ Structured       │
                   │ Document         │
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │ Serializer       │
                   │ MD / Text / JSON │
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │ HybridChunker    │
                   │ max tokens: 512  │
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │ SQLite / JSON    │
                   │ RAG-ready chunks │
                   └──────────────────┘
```

---

# 67. Key Technical Decisions

| Decision | MVP Choice | Reason |
|---|---|---|
| Docling deployment | In-process Python library | Simpler architecture |
| Canonical representation | DoclingDocument | Preserve structure |
| PDF OCR | Enabled, not forced | Support scanned content without unnecessary OCR |
| Table extraction | Enabled | Important for RAG document quality |
| TXT parsing | Native Python | Docling is unnecessary for plain text |
| Chunking | HybridChunker | Structure + tokenizer aware |
| Chunk size | Token based | Better aligned with embedding/LLM context |
| Persistence | SQLite + local filesystem | Low complexity |
| Processing | Synchronous | MVP simplicity |
| XLS legacy | Optional with LibreOffice | Extra runtime dependency |
| Future scaling | Queue / worker or docling-serve | Add only when needed |

---

# 68. Docling vs Previous Tika Architecture

Major architecture change:

```text
Previous
React
  ↓
Flask
  ↓ HTTP
Apache Tika Server
  ↓
Plain / semi-structured extraction
  ↓
Normalizer
  ↓
Generic Chunker
```

New:

```text
React
  ↓
Flask
  ↓ Python
Docling
  ↓
DoclingDocument
  ↓
Structure-aware Serialization
  ↓
HybridChunker
```

Main advantages expected from this design:

- fewer services for MVP;
- richer document structure;
- built-in OCR capabilities;
- improved table handling;
- page/layout provenance;
- built-in RAG-oriented chunking;
- better path toward citation-aware RAG.

Trade-offs:

- heavier Python runtime;
- model downloads/startup may be larger;
- OCR/layout processing can consume more CPU/RAM;
- some features may require additional model/runtime dependencies;
- legacy Office formats may require LibreOffice;
- package/model versions should be pinned and tested.

---

# 69. References

Implementation should be validated against the currently pinned Docling version.

Primary references:

- Docling Documentation — Supported Formats  
  https://docling-project.github.io/docling/usage/supported_formats/
- Docling Documentation / CLI Reference  
  https://docling-project.github.io/docling/reference/cli/
- Docling GitHub  
  https://github.com/docling-project/docling

The project should pin the Docling dependency and update this PRD when parser APIs or supported format behavior changes.
