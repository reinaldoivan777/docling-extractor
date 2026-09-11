import { useState } from "react";

import { ChunkCard } from "../components/ChunkCard";
import { DocumentSummary } from "../components/DocumentSummary";
import { MarkdownViewer } from "../components/MarkdownViewer";
import { MetadataViewer } from "../components/MetadataViewer";
import { StructureViewer } from "../components/StructureViewer";
import { useDocument } from "../hooks/useDocument";

type DocumentPageProps = {
  documentId: string;
  onBackToUpload: () => void;
};

type TabKey = "markdown" | "text" | "structure" | "chunks" | "metadata";

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: "markdown", label: "Markdown" },
  { key: "text", label: "Text" },
  { key: "structure", label: "Structure" },
  { key: "chunks", label: "Chunks" },
  { key: "metadata", label: "Metadata" }
];

export function DocumentPage({ documentId, onBackToUpload }: DocumentPageProps) {
  const { data, loading, error, reload } = useDocument(documentId);
  const [activeTab, setActiveTab] = useState<TabKey>("markdown");

  return (
    <main className="app-shell">
      <section className="top-bar">
        <div>
          <h1>Document RAG Processor</h1>
          <p className="subtle">Result inspection</p>
        </div>
        <div className="top-actions">
          <button type="button" className="ghost-button" onClick={reload}>
            Reload
          </button>
          <button type="button" className="primary-button" onClick={onBackToUpload}>
            New Upload
          </button>
        </div>
      </section>

      {loading ? <section className="message">Loading document...</section> : null}

      {error ? (
        <section className="message error-message">
          <strong>{error.code}</strong>
          <span>{error.message}</span>
        </section>
      ) : null}

      {data ? (
        <>
          <DocumentSummary document={data.summary} />

          <section className="result-panel">
            <div className="tabs" role="tablist" aria-label="Document result tabs">
              {TABS.map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  role="tab"
                  aria-selected={activeTab === tab.key}
                  className={activeTab === tab.key ? "is-active" : ""}
                  onClick={() => setActiveTab(tab.key)}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="tab-body">{renderTab(activeTab, data)}</div>
          </section>
        </>
      ) : null}
    </main>
  );
}

function renderTab(activeTab: TabKey, data: NonNullable<ReturnType<typeof useDocument>["data"]>) {
  switch (activeTab) {
    case "markdown":
      return <MarkdownViewer content={data.content.markdown} />;
    case "text":
      return <MarkdownViewer content={data.content.text || "No text export available."} />;
    case "structure":
      return <StructureViewer structure={data.structure} />;
    case "chunks":
      return (
        <div className="chunk-list">
          {data.chunks.chunks.length ? (
            data.chunks.chunks.map((chunk) => <ChunkCard key={chunk.id} chunk={chunk} />)
          ) : (
            <p className="subtle">No chunks were generated.</p>
          )}
        </div>
      );
    case "metadata":
      return <MetadataViewer value={data.summary.metadata} />;
  }
}
