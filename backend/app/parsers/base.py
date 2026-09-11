from abc import ABC, abstractmethod
from pathlib import Path

from ..models.parsed_document import ParsedDocument


class DocumentParser(ABC):
    @abstractmethod
    def parse(self, file_path: str | Path) -> ParsedDocument:
        raise NotImplementedError
