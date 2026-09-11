import { useEffect, useState } from "react";

import { ApiError, documentApi } from "./services/documentApi";
import "./styles.css";
import { UploadPage } from "./pages/UploadPage";
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

  return <UploadPage health={health} healthError={error} />;
}
