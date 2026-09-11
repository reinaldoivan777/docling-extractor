import type {
  ApiErrorBody,
  DeleteDocumentResponse,
  DocumentChunksResponse,
  DocumentContent,
  DocumentStructure,
  DocumentSummary,
  HealthResponse,
  UploadDocumentOptions
} from "../types/document";

export class ApiError extends Error {
  code: string;
  status: number;
  details?: Record<string, unknown>;

  constructor({
    code,
    message,
    status,
    details
  }: {
    code: string;
    message: string;
    status: number;
    details?: Record<string, unknown>;
  }) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init
  });

  if (!response.ok) {
    throw await normalizeApiError(response);
  }

  return (await response.json()) as T;
}

async function normalizeApiError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as ApiErrorBody;
    if (body.error) {
      return new ApiError({
        code: body.error.code,
        message: body.error.message,
        status: response.status,
        details: body.error.details
      });
    }
  } catch {
    // Fall through to a generic displayable error.
  }

  return new ApiError({
    code: "REQUEST_FAILED",
    message: `Request failed with status ${response.status}.`,
    status: response.status
  });
}

export const documentApi = {
  health(): Promise<HealthResponse> {
    return requestJson<HealthResponse>("/api/health");
  },

  uploadDocument({ file, chunker, maxTokens }: UploadDocumentOptions): Promise<DocumentSummary> {
    const formData = new FormData();
    formData.append("file", file);

    if (chunker) {
      formData.append("chunker", chunker);
    }

    if (maxTokens !== undefined) {
      formData.append("max_tokens", String(maxTokens));
    }

    return requestJson<DocumentSummary>("/api/documents", {
      method: "POST",
      body: formData
    });
  },

  getDocument(documentId: string): Promise<DocumentSummary> {
    return requestJson<DocumentSummary>(`/api/documents/${encodeURIComponent(documentId)}`);
  },

  getContent(documentId: string): Promise<DocumentContent> {
    return requestJson<DocumentContent>(`/api/documents/${encodeURIComponent(documentId)}/content`);
  },

  getStructure(documentId: string): Promise<DocumentStructure> {
    return requestJson<DocumentStructure>(`/api/documents/${encodeURIComponent(documentId)}/structure`);
  },

  getChunks(documentId: string): Promise<DocumentChunksResponse> {
    return requestJson<DocumentChunksResponse>(`/api/documents/${encodeURIComponent(documentId)}/chunks`);
  },

  deleteDocument(documentId: string): Promise<DeleteDocumentResponse> {
    return requestJson<DeleteDocumentResponse>(`/api/documents/${encodeURIComponent(documentId)}`, {
      method: "DELETE"
    });
  }
};
