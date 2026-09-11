import { useState } from "react";

import type { DocumentChunk } from "../types/document";

type ChunkCardProps = {
  chunk: DocumentChunk;
};

export function ChunkCard({ chunk }: ChunkCardProps) {
  const [showContextualized, setShowContextualized] = useState(true);
  const [copied, setCopied] = useState(false);
  const content = showContextualized ? chunk.contextualized_content : chunk.content;
  const headings = chunk.metadata.headings ?? [];
  const pages = chunk.metadata.page_numbers ?? [];

  async function copyContent() {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  }

  return (
    <article className="chunk-card">
      <header className="chunk-header">
        <div>
          <h3>Chunk #{chunk.index + 1}</h3>
          <p>
            {chunk.token_count ?? "-"} tokens
            {pages.length ? ` · Pages ${pages.join(", ")}` : ""}
          </p>
        </div>
        <div className="chunk-actions">
          <label className="toggle-control">
            <input
              type="checkbox"
              checked={showContextualized}
              onChange={(event) => setShowContextualized(event.target.checked)}
            />
            Context
          </label>
          <button type="button" className="ghost-button" onClick={copyContent}>
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </header>

      {headings.length ? (
        <div className="tag-row">
          {headings.map((heading) => (
            <span key={heading}>{heading}</span>
          ))}
        </div>
      ) : null}

      <pre className="content-block">{content}</pre>
    </article>
  );
}
