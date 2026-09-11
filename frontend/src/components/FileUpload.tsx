import { ChangeEvent, DragEvent, useRef, useState } from "react";

const ACCEPTED_EXTENSIONS = ".pdf,.docx,.txt,.md,.xlsx,.xls,.csv";

type FileUploadProps = {
  file: File | null;
  disabled?: boolean;
  maxUploadSizeMb?: number;
  onFileChange: (file: File | null) => void;
};

export function FileUpload({ file, disabled = false, maxUploadSizeMb = 20, onFileChange }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    onFileChange(event.target.files?.[0] ?? null);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);

    if (disabled) {
      return;
    }

    onFileChange(event.dataTransfer.files?.[0] ?? null);
  }

  function handleDragOver(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    if (!disabled) {
      setDragging(true);
    }
  }

  return (
    <div className="upload-control">
      <label
        className={`drop-zone${dragging ? " is-dragging" : ""}${disabled ? " is-disabled" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS}
          disabled={disabled}
          onChange={handleInputChange}
        />
        <span className="drop-zone-title">Drop document here</span>
        <span className="drop-zone-meta">PDF DOCX TXT MD XLSX XLS CSV · max {maxUploadSizeMb} MB</span>
      </label>

      {file ? (
        <div className="selected-file">
          <div>
            <span className="field-label">Selected</span>
            <strong>{file.name}</strong>
          </div>
          <span>{formatFileSize(file.size)}</span>
          <button type="button" className="ghost-button" disabled={disabled} onClick={() => onFileChange(null)}>
            Clear
          </button>
        </div>
      ) : null}
    </div>
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
