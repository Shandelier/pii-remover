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

    COMMON_FIRST_NAMES = {
        "adam",
        "alicja",
        "anna",
        "anno",
        "ewa",
        "james",
        "jan",
        "jana",
        "jane",
        "jerzy",
        "john",
        "katarzyna",
        "marta",
        "michał",
        "michal",
        "paweł",
        "pawel",
        "piotr",
        "tomasz",
    }

    COMMON_LAST_NAMES = {
        "bond",
        "kowalski",
        "kowalskiego",
        "kowalska",
        "nowak",
        "wiśniewska",
        "wisniewska",
        "zieliński",
        "zielinski",
    }

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
        ("PERSON", r"\b[A-ZŁŚŻŹĆŃÓĘ][a-ząćęłńóśźż-]{2,}\s+[A-ZŁŚŻŹĆŃÓĘ][a-ząćęłńóśźż-]{2,}\b"),
        ("PERSON", r"\b[A-ZŁŚŻŹĆŃÓĘ][a-ząćęłńóśźż-]{2,}\b"),
    )

    def __init__(self, threshold: float = 0.0) -> None:
        self.threshold = threshold
        self._compiled = [(label, re.compile(pattern, re.IGNORECASE)) for label, pattern in self.PATTERNS]

    def detect(self, text: str) -> list[Span]:
        spans: list[Span] = []
        for label, pattern in self._compiled:
            for match in pattern.finditer(text):
                if label == "PERSON":
                    span = self._person_span_from_match(match)
                    if span is not None:
                        spans.append(span)
                    continue
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
        if label == "PERSON":
            return self._looks_like_person(value)
        return True

    def _looks_like_person(self, value: str) -> bool:
        raw_words = re.findall(r"[A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ-]{3,}", value)
        words = [word.lower() for word in raw_words]
        known = [word in self.COMMON_FIRST_NAMES or word in self.COMMON_LAST_NAMES for word in words]
        if len(words) >= 2:
            all_known = all(known)
            has_capitalized_name = any(word[:1].isupper() for word in raw_words) and any(known)
            return all_known or has_capitalized_name
        if len(words) == 1:
            return known[0]
        return False

    def _person_span_from_match(self, match: re.Match[str]) -> Span | None:
        value = match.group(0)
        word_matches = list(re.finditer(r"[A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ-]{3,}", value))
        words = [word_match.group(0).lower() for word_match in word_matches]
        known_indexes = [
            index
            for index, word in enumerate(words)
            if word in self.COMMON_FIRST_NAMES or word in self.COMMON_LAST_NAMES
        ]
        if not known_indexes:
            return None

        if value.lower().startswith(("pan ", "pani ")) and len(known_indexes) == 1:
            return Span(match.start(), match.end(), "PERSON", 1.0)

        if len(words) == 1:
            word_match = word_matches[0]
            return Span(match.start() + word_match.start(), match.start() + word_match.end(), "PERSON", 1.0)

        if len(known_indexes) >= 2:
            first = word_matches[known_indexes[0]]
            last = word_matches[known_indexes[-1]]
            return Span(match.start() + first.start(), match.start() + last.end(), "PERSON", 1.0)

        has_capitalized_word = any(word_match.group(0)[:1].isupper() for word_match in word_matches)
        if has_capitalized_word:
            first_known = word_matches[known_indexes[0]]
            return Span(match.start() + first_known.start(), match.start() + first_known.end(), "PERSON", 1.0)

        return None


class BardsAiOnnxDetector:
    """Local ONNX Runtime backend for bardsai/eu-pii-anonimization-multilang."""

    def __init__(
        self,
        model_id: str = "bardsai/eu-pii-anonimization-multilang",
        threshold: float = 0.5,
    ) -> None:
        self.threshold = threshold
        try:
            import json

            import numpy as np
            import onnxruntime as ort
            from huggingface_hub import hf_hub_download
            from tokenizers import Tokenizer
        except ImportError as exc:
            raise RuntimeError(
                "Install local model dependencies with `python3 -m pip install -e '.[local]'`."
            ) from exc

        tokenizer_path = hf_hub_download(model_id, "tokenizer.json")
        config_path = hf_hub_download(model_id, "config.json")
        model_path = hf_hub_download(model_id, "onnx/model_quantized.onnx")

        with open(config_path, encoding="utf-8") as file:
            config = json.load(file)

        self.id2label = {int(key): value for key, value in config["id2label"].items()}
        self._np = np
        self._tokenizer = Tokenizer.from_file(tokenizer_path)
        self._regex_detector = RegexDetector(threshold=0.0)

        session_options = ort.SessionOptions()
        session_options.intra_op_num_threads = 1
        session_options.inter_op_num_threads = 1
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
        self._session = ort.InferenceSession(
            model_path,
            sess_options=session_options,
            providers=["CPUExecutionProvider"],
        )
        self._input_names = {model_input.name for model_input in self._session.get_inputs()}
        self._output_name = self._session.get_outputs()[0].name

    def detect(self, text: str) -> list[Span]:
        if not text:
            return []

        encoding = self._tokenizer.encode(text)
        np = self._np
        inputs = {
            "input_ids": np.array([encoding.ids], dtype=np.int64),
            "attention_mask": np.array([encoding.attention_mask], dtype=np.int64),
        }
        if "token_type_ids" in self._input_names:
            inputs["token_type_ids"] = np.array([encoding.type_ids], dtype=np.int64)

        outputs = self._session.run([self._output_name], inputs)
        logits = outputs[0][0]
        probabilities = _softmax(logits)
        label_ids = probabilities.argmax(axis=-1)
        scores = probabilities.max(axis=-1)

        model_spans = self._bio_to_spans(
            label_ids=label_ids,
            scores=scores,
            offsets=encoding.offsets,
            word_ids=encoding.word_ids,
        )
        return _dedupe_and_merge([*model_spans, *self._regex_detector.detect(text)])

    def _bio_to_spans(
        self,
        label_ids,
        scores,
        offsets: list[tuple[int, int]],
        word_ids: list[int | None],
    ) -> list[Span]:
        spans: list[Span] = []
        current_start: int | None = None
        current_end: int | None = None
        current_label: str | None = None
        current_scores: list[float] = []

        for label_id, score, offset, word_id in zip(label_ids, scores, offsets, word_ids, strict=True):
            start, end = offset
            if start == end or word_id is None:
                continue

            raw_label = self.id2label[int(label_id)]
            if raw_label == "O" or float(score) < self.threshold:
                if current_start is not None and current_label is not None and current_end is not None:
                    spans.append(Span(current_start, current_end, current_label, min(current_scores)))
                current_start = current_end = current_label = None
                current_scores = []
                continue

            prefix, entity = raw_label.split("-", 1)
            starts_new_span = (
                prefix == "B"
                or current_label != entity
                or current_start is None
                or (current_end is not None and start > current_end + 1)
            )
            if starts_new_span:
                if current_start is not None and current_label is not None and current_end is not None:
                    spans.append(Span(current_start, current_end, current_label, min(current_scores)))
                current_start = start
                current_label = entity
                current_scores = [float(score)]
            else:
                current_scores.append(float(score))

            current_end = end

        if current_start is not None and current_label is not None and current_end is not None:
            spans.append(Span(current_start, current_end, current_label, min(current_scores)))

        return spans


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
        if not merged:
            merged.append(span)
            continue
        previous = merged[-1]
        if previous.label == span.label and span.start <= previous.end + 1:
            merged[-1] = Span(previous.start, max(previous.end, span.end), previous.label, min(previous.score, span.score))
            continue
        if not previous.overlaps(span):
            merged.append(span)
            continue
        if span.end > previous.end:
            merged[-1] = Span(previous.start, span.end, previous.label, max(previous.score, span.score))
    return merged


def _softmax(logits):
    import numpy as np

    shifted = logits - logits.max(axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=-1, keepdims=True)
