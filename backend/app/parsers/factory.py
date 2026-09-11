from collections.abc import Callable

from ..config import AppConfig
from ..utils.errors import UnsupportedFileTypeError
from .base import DocumentParser
from .docling_parser import DoclingParser
from .text_parser import TextParser


ParserBuilder = Callable[[], DocumentParser]


class ParserFactory:
    DOCLING_EXTENSIONS = {".pdf", ".docx", ".md", ".xlsx", ".xls", ".csv"}
    TEXT_EXTENSIONS = {".txt"}

    def __init__(
        self,
        config: AppConfig,
        *,
        docling_parser_builder: ParserBuilder | None = None,
        text_parser_builder: ParserBuilder | None = None,
    ):
        self.config = config
        self.docling_parser_builder = docling_parser_builder or DoclingParser
        self.text_parser_builder = text_parser_builder or TextParser

    def get(self, extension: str) -> DocumentParser:
        normalized_extension = extension.lower()

        if normalized_extension not in self.config.allowed_extensions:
            raise UnsupportedFileTypeError()

        if normalized_extension == ".xls" and not self.config.enable_legacy_xls:
            raise UnsupportedFileTypeError("Legacy XLS support is disabled.")

        if normalized_extension in self.TEXT_EXTENSIONS:
            return self.text_parser_builder()

        if normalized_extension in self.DOCLING_EXTENSIONS:
            return self.docling_parser_builder()

        raise UnsupportedFileTypeError()
