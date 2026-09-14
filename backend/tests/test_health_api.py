from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest
from unittest.mock import patch

from backend.app import create_app
from backend.app.utils.errors import ErrorCode


class HealthApiTest(unittest.TestCase):
    def test_health_reports_degraded_docling_initialization(self):
        blocked_modules = {
            name: None
            for name in [
                "docling",
                "docling.datamodel",
                "docling.datamodel.base_models",
                "docling.datamodel.pipeline_options",
                "docling.document_converter",
            ]
        }
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with patch.dict(
                "os.environ",
                {
                    "DATABASE_URL": f"sqlite:///{root / 'app.db'}",
                    "STORAGE_PATH": str(root / "documents"),
                },
            ), patch.dict(sys.modules, blocked_modules):
                app = create_app()
                response = app.test_client().get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "degraded")
        self.assertEqual(response.json["services"]["docling"], "initialization_failed")
        self.assertFalse(response.json["docling"]["ready"])
        self.assertEqual(
            response.json["docling"]["error_code"],
            ErrorCode.DOCLING_INITIALIZATION_FAILED.value,
        )


if __name__ == "__main__":
    unittest.main()
