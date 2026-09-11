import { useEffect, useState } from "react";

import { ApiError, documentApi } from "../services/documentApi";
import type { LoadedDocument } from "../types/document";

export type UseDocumentState = {
  data: LoadedDocument | null;
  loading: boolean;
  error: ApiError | null;
  reload: () => void;
};

export function useDocument(documentId: string | null): UseDocumentState {
  const [data, setData] = useState<LoadedDocument | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    if (!documentId) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setError(null);

    Promise.all([
      documentApi.getDocument(documentId),
      documentApi.getContent(documentId),
      documentApi.getStructure(documentId),
      documentApi.getChunks(documentId)
    ])
      .then(([summary, content, structure, chunks]) => {
        if (!controller.signal.aborted) {
          setData({ summary, content, structure, chunks });
        }
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            caught instanceof ApiError
              ? caught
              : new ApiError({
                  code: "REQUEST_FAILED",
                  message: caught instanceof Error ? caught.message : "Unable to load document.",
                  status: 0
                })
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => {
      controller.abort();
    };
  }, [documentId, reloadToken]);

  return {
    data,
    loading,
    error,
    reload: () => setReloadToken((token) => token + 1)
  };
}
