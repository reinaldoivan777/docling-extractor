import type { DocumentSummary as DocumentSummaryType } from "../types/document";

type DocumentSummaryProps = {
  document: DocumentSummaryType;
};

export function DocumentSummary({ document }: DocumentSummaryProps) {
  const processing = document.processing;

  return (
    <section className="summary-band" aria-label="Document summary">
      <div>
        <span className="field-label">Document</span>
        <h2>{document.filename}</h2>
      </div>
      <dl className="summary-grid">
        <div>
          <dt>Status</dt>
          <dd>{document.status}</dd>
        </div>
        <div>
          <dt>Type</dt>
          <dd>{document.content_type}</dd>
        </div>
        <div>
          <dt>Size</dt>
          <dd>{formatFileSize(document.size)}</dd>
        </div>
        <div>
          <dt>Pages</dt>
          <dd>{processing?.page_count ?? "-"}</dd>
        </div>
        <div>
          <dt>Tables</dt>
          <dd>{processing?.table_count ?? "-"}</dd>
        </div>
        <div>
          <dt>Chunks</dt>
          <dd>{processing?.chunk_count ?? document.chunk_count ?? 0}</dd>
        </div>
        <div>
          <dt>OCR</dt>
          <dd>{processing?.ocr_used === null || processing?.ocr_used === undefined ? "Unknown" : processing.ocr_used ? "Used" : "Not used"}</dd>
        </div>
      </dl>
    </section>
  );
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
