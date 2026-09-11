export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
};

export type HealthResponse = {
  status: "ok" | "degraded" | string;
  services: {
    api: string;
    docling: string;
  };
  docling?: {
    ready: boolean;
    status: string;
    ocr_enabled: boolean;
    table_structure_enabled: boolean;
    xls_support: boolean;
    error_code?: string;
    error_message?: string;
  };
  config?: {
    max_upload_size_mb: number;
    max_document_pages: number;
    processing_timeout_seconds: number;
    default_chunker: string;
    default_chunk_max_tokens: number;
    legacy_xls_enabled: boolean;
  };
};

export type DocumentProcessingSummary = {
  page_count: number | null;
  markdown_character_count: number | null;
  chunk_count: number;
  ocr_used: boolean | null;
  table_count: number | null;
  picture_count: number | null;
};

export type DocumentError = {
  code: string;
  message: string;
} | null;

export type DocumentSummary = {
  id: string;
  filename: string;
  content_type: string;
  extension: string;
  size: number;
  status: string;
  created_at?: string;
  updated_at?: string;
  processing?: DocumentProcessingSummary;
  metadata: Record<string, unknown>;
  error?: DocumentError;
  chunk_count?: number;
};

export type UploadDocumentOptions = {
  file: File;
  chunker?: string;
  maxTokens?: number;
};

export type DocumentContent = {
  document_id: string;
  markdown: string;
  text: string;
  available_exports: Array<"markdown" | "text" | "json" | string>;
};

export type DocumentStructure = {
  document_id: string;
  pages: number | null;
  tables: number | null;
  pictures: number | null;
  headings: string[];
  source_format: string;
  metadata: {
    ocr_used: boolean | null;
    markdown_character_count: number | null;
    chunk_count: number;
    artifacts: Record<string, unknown>;
  };
};

export type DocumentChunk = {
  id: string;
  document_id: string;
  index: number;
  content: string;
  contextualized_content: string;
  token_count: number | null;
  metadata: {
    filename?: string | null;
    source_format?: string;
    headings?: string[];
    page_numbers?: number[];
    captions?: string[];
    table_refs?: string[];
    source_items?: string[];
    [key: string]: unknown;
  };
  created_at?: string;
};

export type DocumentChunksResponse = {
  document_id: string;
  count: number;
  chunks: DocumentChunk[];
};

export type DeleteDocumentResponse = {
  success: boolean;
};

export type LoadedDocument = {
  summary: DocumentSummary;
  content: DocumentContent;
  structure: DocumentStructure;
  chunks: DocumentChunksResponse;
};
