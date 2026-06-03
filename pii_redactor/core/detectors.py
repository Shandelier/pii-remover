from __future__ import annotations

import re
from typing import Protocol

from pii_redactor.core.types import Span


class Detector(Protocol):
    def detect(self, text: str) -> list[Span]:
        ...


class RegexDetector:
    """Small deterministic fallback for demos and tests.

    The production path is BardsAiOnnxDetector. This keeps the prototype usable
    without forcing every local demo to download model weights first.
    """

    PATTERNS: tuple[tuple[str, str], ...] = (
        ("EMAIL", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        ("PHONE", r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)"),
        ("PESEL", r"\b\d{11}\b"),
        ("CREDIT_CARD", r"\b(?:\d[ -]*?){13,19}\b"),
        ("IBAN", r"\b[A-Z]{2}\d{2}(?:[ -]?[A-Z0-9]){11,30}\b"),
        ("IP_ADDRESS", r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
        ("POSTAL_CODE", r"\b\d{2}-\d{3}\b"),
        ("ADDRESS", r"\b(?:ul\.|ulica|al\.|aleja)\s+[A-ZŁŚŻŹĆŃÓĘ][\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ.-]+(?:\s+\d+[A-Za-z]?/?\d*)?\b"),
        ("PERSON", r"\b(?:Pan|Pani)\s+(?:Janie|Anno|Piotrze|Marto|Tomaszu|Katarzyno|Adamie|Alicjo|Michale|Ewo)\b"),
        ("PERSON", r"\b(?:Jana Kowalskiego|Anny Nowak|Piotra Zielińskiego|Marty Wiśniewskiej)\b"),
        ("PERSON", r"\b(?:Jan|Anna|Piotr|Marta|Tomasz|Katarzyna|Adam|Alicja|Michał|Ewa)\s+[A-ZŁŚŻŹĆŃÓĘ][a-ząćęłńóśźż-]+\b"),
    )

    def __init__(self, threshold: float = 0.0) -> None:
        self.threshold = threshold
        self._compiled = [(label, re.compile(pattern, re.IGNORECASE)) for label, pattern in self.PATTERNS]

    def detect(self, text: str) -> list[Span]:
        spans: list[Span] = []
        for label, pattern in self._compiled:
            for match in pattern.finditer(text):
                if not self._looks_like_valid_span(label, match.group(0)):
                    continue
                spans.append(Span(match.start(), match.end(), label, 1.0))
        return _dedupe_and_merge(spans)

    def _looks_like_valid_span(self, label: str, value: str) -> bool:
        digits = re.sub(r"\D", "", value)
        if label == "PHONE":
            return 9 <= len(digits) <= 15
        if label == "CREDIT_CARD":
            return 13 <= len(digits) <= 19
        if label == "IP_ADDRESS":
            return all(0 <= int(part) <= 255 for part in value.split("."))
        return True


class BardsAiOnnxDetector:
    """Optional local model backend for bardsai/eu-pii-anonimization-multilang."""

    def __init__(
        self,
        model_id: str = "bardsai/eu-pii-anonimization-multilang",
        threshold: float = 0.5,
        aggregation_strategy: str = "simple",
    ) -> None:
        self.threshold = threshold
        try:
            from optimum.onnxruntime import ORTModelForTokenClassification
            from transformers import AutoTokenizer, pipeline
        except ImportError as exc:
            raise RuntimeError(
                "Install local model dependencies with `pip install -e '.[local]'`."
            ) from exc

        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = ORTModelForTokenClassification.from_pretrained(model_id, file_name="onnx/model_quantized.onnx")
        self._pipeline = pipeline(
            "token-classification",
            model=model,
            tokenizer=tokenizer,
            aggregation_strategy=aggregation_strategy,
        )

    def detect(self, text: str) -> list[Span]:
        entities = self._pipeline(text)
        spans = [
            Span(int(entity["start"]), int(entity["end"]), str(entity["entity_group"]), float(entity["score"]))
            for entity in entities
            if float(entity["score"]) >= self.threshold
        ]
        return _dedupe_and_merge(spans)


def build_detector(backend: str = "regex", threshold: float = 0.5) -> Detector:
    if backend == "regex":
        return RegexDetector(threshold=threshold)
    if backend in {"local", "bardsai"}:
        return BardsAiOnnxDetector(threshold=threshold)
    raise ValueError(f"Unsupported detector backend: {backend}")


def _dedupe_and_merge(spans: list[Span]) -> list[Span]:
    ordered = sorted(spans, key=lambda span: (span.start, -(span.end - span.start)))
    merged: list[Span] = []
    for span in ordered:
        if span.start >= span.end:
            continue
        if not merged or not merged[-1].overlaps(span):
            merged.append(span)
            continue
        previous = merged[-1]
        if span.end > previous.end:
            merged[-1] = Span(previous.start, span.end, previous.label, max(previous.score, span.score))
    return merged
