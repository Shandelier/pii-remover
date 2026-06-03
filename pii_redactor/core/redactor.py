from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pii_redactor.core.detectors import Detector, build_detector
from pii_redactor.core.types import Span


class Redactor:
    def __init__(
        self,
        detector: Detector | None = None,
        replacement: str = "[REDACTED]",
        max_depth: int = 20,
    ) -> None:
        self.detector = detector or build_detector()
        self.replacement = replacement
        self.max_depth = max_depth

    def detect(self, text: str) -> list[Span]:
        return self.detector.detect(text)

    def redact_text(self, text: str) -> str:
        spans = self.detect(text)
        if not spans:
            return text

        chunks: list[str] = []
        cursor = 0
        for span in spans:
            chunks.append(text[cursor:span.start])
            chunks.append(self.replacement)
            cursor = span.end
        chunks.append(text[cursor:])
        return "".join(chunks)

    def redact(self, data: Any, depth: int = 0) -> Any:
        if depth > self.max_depth:
            return self.replacement
        if isinstance(data, str):
            return self.redact_text(data)
        if isinstance(data, Mapping):
            return {key: self.redact(value, depth + 1) for key, value in data.items()}
        if isinstance(data, tuple):
            return tuple(self.redact(value, depth + 1) for value in data)
        if isinstance(data, Sequence) and not isinstance(data, (bytes, bytearray)):
            return [self.redact(value, depth + 1) for value in data]
        return data
