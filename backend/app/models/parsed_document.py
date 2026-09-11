from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ParsedDocument:
    source_format: str
    structured_document: Any
    markdown: str = ""
    text: str = ""
    metadata: dict = field(default_factory=dict)
