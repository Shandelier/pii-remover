from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any

from pii_redactor.core.detectors import Detector, build_detector
from pii_redactor.core.types import Span


class Redactor:
    def __init__(
        self,
        detector: Detector | None = None,
        replacement: str = "[REDACTED]",
        max_depth: int = 20,
        include_labels: set[str] | None = None,
        exclude_labels: set[str] | None = None,
        expand_to_word_boundaries: bool = True,
    ) -> None:
        self.detector = detector or build_detector()
        self.replacement = replacement
        self.max_depth = max_depth
        self.include_labels = include_labels
        self.exclude_labels = exclude_labels or set()
        self.expand_to_word_boundaries = expand_to_word_boundaries

    def detect(self, text: str) -> list[Span]:
        spans = self.detector.detect(text)
        return [span for span in spans if self._should_redact(span)]

    def redact_text(self, text: str) -> str:
        spans = self._prepare_spans(text, self.detect(text))
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

    def _should_redact(self, span: Span) -> bool:
        if self.include_labels is not None and span.label not in self.include_labels:
            return False
        return span.label not in self.exclude_labels

    def _prepare_spans(self, text: str, spans: list[Span]) -> list[Span]:
        if not self.expand_to_word_boundaries:
            return spans

        expanded = [self._expand_span_to_word_boundaries(text, span) for span in spans]
        return _merge_spans(expanded)

    def _expand_span_to_word_boundaries(self, text: str, span: Span) -> Span:
        start = max(0, min(span.start, len(text)))
        end = max(start, min(span.end, len(text)))
        while start > 0 and _is_word_char(text[start - 1]):
            start -= 1
        while end < len(text) and _is_word_char(text[end]):
            end += 1
        return Span(start, end, span.label, span.score)

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


def _is_word_char(character: str) -> bool:
    return re.match(r"[\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ-]", character, flags=re.UNICODE) is not None


def _merge_spans(spans: list[Span]) -> list[Span]:
    merged: list[Span] = []
    for span in sorted(spans, key=lambda item: (item.start, item.end)):
        if not merged or span.start > merged[-1].end:
            merged.append(span)
            continue
        previous = merged[-1]
        merged[-1] = Span(previous.start, max(previous.end, span.end), previous.label, min(previous.score, span.score))
    return merged
