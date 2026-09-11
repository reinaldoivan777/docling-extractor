import type { DocumentStructure } from "../types/document";

type StructureViewerProps = {
  structure: DocumentStructure;
};

export function StructureViewer({ structure }: StructureViewerProps) {
  return (
    <div className="structure-view">
      <dl className="summary-grid">
        <div>
          <dt>Pages</dt>
          <dd>{structure.pages ?? "-"}</dd>
        </div>
        <div>
          <dt>Headings</dt>
          <dd>{structure.headings.length}</dd>
        </div>
        <div>
          <dt>Tables</dt>
          <dd>{structure.tables ?? "-"}</dd>
        </div>
        <div>
          <dt>Pictures</dt>
          <dd>{structure.pictures ?? "-"}</dd>
        </div>
      </dl>

      <div className="heading-list">
        {structure.headings.length ? (
          structure.headings.map((heading) => <div key={heading}>{heading}</div>)
        ) : (
          <p className="subtle">No headings were reported.</p>
        )}
      </div>
    </div>
  );
}
