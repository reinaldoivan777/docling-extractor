import { FormEvent, useMemo, useState } from "react";

import { FileUpload } from "../components/FileUpload";
import { ProcessingStatus } from "../components/ProcessingStatus";
import { ApiError, documentApi } from "../services/documentApi";
import type { DocumentSummary, HealthResponse } from "../types/document";

type UploadPageProps = {
  health: HealthResponse | null;
  healthError: string | null;
};

export function UploadPage({ health, healthError }: UploadPageProps) {
  const [file, setFile] = useState<File | null>(null);
  const [chunker, setChunker] = useState("hybrid");
  const [maxTokens, setMaxTokens] = useState(health?.config?.default_chunk_max_tokens ?? 512);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [completedDocument, setCompletedDocument] = useState<DocumentSummary | null>(null);

  const maxUploadSizeMb = health?.config?.max_upload_size_mb ?? 20;
  const pdfOcrMode = health?.docling?.ocr_enabled ? "Auto" : "Off";

  const canSubmit = useMemo(() => Boolean(file) && !submitting, [file, submitting]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError(new ApiError({ code: "NO_FILE", message: "Select a document before processing.", status: 0 }));
      return;
    }

    setSubmitting(true);
    setError(null);
    setCompletedDocument(null);

    try {
      const document = await documentApi.uploadDocument({ file, chunker, maxTokens });
      setCompletedDocument(document);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught
          : new ApiError({
              code: "UPLOAD_FAILED",
              message: caught instanceof Error ? caught.message : "Upload failed.",
              status: 0
            })
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="top-bar" aria-label="System status">
        <div>
          <h1>Document RAG Processor</h1>
          <p className="subtle">Docling Edition</p>
        </div>
        <StatusPill health={health} error={healthError} />
      </section>

      <form className="workspace" onSubmit={handleSubmit}>
        <section className="upload-panel" aria-label="Upload document">
          <FileUpload file={file} disabled={submitting} maxUploadSizeMb={maxUploadSizeMb} onFileChange={setFile} />
        </section>

        <section className="settings-panel" aria-label="Processing configuration">
          <div className="field-grid">
            <label>
              <span className="field-label">Chunker</span>
              <select value={chunker} disabled={submitting} onChange={(event) => setChunker(event.target.value)}>
                <option value="hybrid">Hybrid</option>
                <option value="hierarchical">Hierarchical</option>
              </select>
            </label>

            <label>
              <span className="field-label">Max Tokens</span>
              <input
                type="number"
                min={1}
                step={1}
                value={maxTokens}
                disabled={submitting}
                onChange={(event) => setMaxTokens(Number(event.target.value))}
              />
            </label>

            <label>
              <span className="field-label">PDF OCR</span>
              <input value={pdfOcrMode} readOnly />
            </label>
          </div>

          <button type="submit" className="primary-button" disabled={!canSubmit}>
            {submitting ? "Processing..." : "Process"}
          </button>
        </section>

        <ProcessingStatus active={submitting} completed={completedDocument?.status === "COMPLETED"} />

        {error ? (
          <section className="message error-message" aria-live="polite">
            <strong>{error.code}</strong>
            <span>{error.message}</span>
          </section>
        ) : null}

        {completedDocument ? (
          <section className="message result-message" aria-live="polite">
            <div>
              <strong>{completedDocument.filename}</strong>
              <span>{completedDocument.status}</span>
            </div>
            <dl>
              <div>
                <dt>Type</dt>
                <dd>{completedDocument.content_type}</dd>
              </div>
              <div>
                <dt>Size</dt>
                <dd>{formatFileSize(completedDocument.size)}</dd>
              </div>
              <div>
                <dt>Chunks</dt>
                <dd>{completedDocument.chunk_count ?? 0}</dd>
              </div>
            </dl>
          </section>
        ) : null}
      </form>
    </main>
  );
}

function StatusPill({ health, error }: { health: HealthResponse | null; error: string | null }) {
  if (error) {
    return <span className="status-pill is-error">API unavailable</span>;
  }

  if (!health) {
    return <span className="status-pill">Checking API</span>;
  }

  return <span className={`status-pill ${health.status === "ok" ? "is-ok" : "is-warn"}`}>{health.services.docling}</span>;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  const kb = bytes / 1024;
  if (kb < 1024) {
    return `${kb.toFixed(1)} KB`;
  }

  return `${(kb / 1024).toFixed(1)} MB`;
}
