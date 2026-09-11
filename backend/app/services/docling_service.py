from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Any

from ..config import AppConfig
from ..utils.errors import AppError, ErrorCode


@dataclass(frozen=True)
class DoclingReadiness:
    ready: bool
    status: str
    ocr_enabled: bool
    table_structure_enabled: bool
    xls_support: bool
    error_code: str | None = None
    error_message: str | None = None


class DoclingService:
    def __init__(self, config: AppConfig):
        self.config = config
        self._converter: Any | None = None
        self._initialization_error: AppError | None = None
        self._xls_support = self._detect_xls_support()

        try:
            self._converter = self._build_converter()
        except AppError as error:
            self._initialization_error = error

    @property
    def converter(self) -> Any:
        if self._initialization_error is not None:
            raise self._initialization_error

        if self._converter is None:
            raise AppError(
                code=ErrorCode.DOCLING_INITIALIZATION_FAILED,
                message="Docling converter is not initialized.",
            )

        return self._converter

    def readiness(self) -> DoclingReadiness:
        if self._initialization_error is not None:
            return DoclingReadiness(
                ready=False,
                status="initialization_failed",
                ocr_enabled=self.config.docling_ocr_enabled,
                table_structure_enabled=self.config.docling_table_structure_enabled,
                xls_support=self._xls_support,
                error_code=self._initialization_error.code.value,
                error_message=self._initialization_error.message,
            )

        return DoclingReadiness(
            ready=True,
            status="ready",
            ocr_enabled=self.config.docling_ocr_enabled,
            table_structure_enabled=self.config.docling_table_structure_enabled,
            xls_support=self._xls_support,
        )

    def convert(self, file_path: str | Path) -> Any:
        result = self.converter.convert(str(file_path))
        return result.document

    def ensure_xls_support(self) -> None:
        if self.config.enable_legacy_xls and not self._xls_support:
            raise AppError(
                code=ErrorCode.XLS_RUNTIME_UNAVAILABLE,
                message="Legacy XLS support requires LibreOffice runtime.",
            )

    def _detect_xls_support(self) -> bool:
        if not self.config.enable_legacy_xls:
            return False

        return shutil.which("soffice") is not None or shutil.which("libreoffice") is not None

    def _build_converter(self) -> Any:
        try:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
            from docling.document_converter import DocumentConverter, PdfFormatOption
        except ImportError as error:
            raise AppError(
                code=ErrorCode.DOCLING_INITIALIZATION_FAILED,
                message="Docling is not installed or could not be imported.",
            ) from error

        try:
            pdf_options = PdfPipelineOptions()
            pdf_options.do_ocr = self.config.docling_ocr_enabled
            pdf_options.do_table_structure = self.config.docling_table_structure_enabled

            # Docling table mode APIs have changed between versions, so keep this best-effort.
            table_structure_options = getattr(pdf_options, "table_structure_options", None)
            if table_structure_options is not None and hasattr(table_structure_options, "mode"):
                table_structure_options.mode = TableFormerMode(self.config.docling_table_mode)

            return DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
                }
            )
        except Exception as error:
            raise AppError(
                code=ErrorCode.DOCLING_INITIALIZATION_FAILED,
                message="Docling converter initialization failed.",
            ) from error
