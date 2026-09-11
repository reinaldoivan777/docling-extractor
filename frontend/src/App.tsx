import { useEffect, useState } from "react";

import { ApiError, documentApi } from "./services/documentApi";
import "./styles.css";
import type { HealthResponse } from "./types/document";

export function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    documentApi
      .health()
      .then(setHealth)
      .catch((caught: unknown) => {
        setError(caught instanceof ApiError ? caught.message : "Health check failed");
      });
  }, []);

  return (
    <main className="app-shell">
      <section className="intro">
        <p className="eyebrow">Docling Edition</p>
        <h1>Document RAG Processor</h1>
        <p>
          Upload, inspect, and chunk documents for retrieval workflows. The scaffold is ready for
          the processing pipeline.
        </p>
      </section>

      <section className="status-panel" aria-label="Backend status">
        <h2>API Health</h2>
        {health ? (
          <dl>
            <div>
              <dt>Status</dt>
              <dd>{health.status}</dd>
            </div>
            <div>
              <dt>API</dt>
              <dd>{health.services.api}</dd>
            </div>
            <div>
              <dt>Docling</dt>
              <dd>{health.services.docling}</dd>
            </div>
          </dl>
        ) : (
          <p>{error ?? "Checking backend..."}</p>
        )}
      </section>
    </main>
  );
}
