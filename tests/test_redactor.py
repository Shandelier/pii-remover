from pii_redactor.core.redactor import Redactor
from pii_redactor.core.types import Span


class StaticDetector:
    def __init__(self, spans: list[Span]) -> None:
        self.spans = spans

    def detect(self, text: str) -> list[Span]:
        return self.spans


def test_redacts_langfuse_shaped_trace_payload() -> None:
    redactor = Redactor()

    result = redactor.redact(
        {
            "input": "Jan Kowalski ma email jan.kowalski@example.com i PESEL 85010112345.",
            "output": "Odpowiedź dla Jana Kowalskiego powinna być zapisana bez danych kontaktowych.",
            "metadata": {"customer_contact": "+48 501 222 333"},
        }
    )

    assert result["input"] == "[REDACTED] ma email [REDACTED] i PESEL [REDACTED]."
    assert result["output"] == "Odpowiedź dla [REDACTED] powinna być zapisana bez danych kontaktowych."
    assert result["metadata"]["customer_contact"] == "[REDACTED]"


def test_store_receives_redacted_values_only(tmp_path) -> None:
    from pii_redactor.store import JsonlStore

    store = JsonlStore(tmp_path / "logs.jsonl")
    store.append("[REDACTED]", "Odpowiedz dla [REDACTED]", "demo")

    content = (tmp_path / "logs.jsonl").read_text()
    assert "[REDACTED]" in content
    assert "jan.kowalski@example.com" not in content


def test_redacts_simple_polish_vocative_name() -> None:
    redactor = Redactor()

    result = redactor.redact_text("Szanowna Pani Anno, proszę o kontakt.")

    assert result == "Szanowna [REDACTED], proszę o kontakt."


def test_redacts_common_free_form_names_from_playground_text() -> None:
    redactor = Redactor()

    result = redactor.redact_text(
        "My name is James, James Bond. Kowalski Jerzy. ukryj jerzy i Ewentualnie paweł kowalski."
    )

    assert result == "My name is [REDACTED], [REDACTED]. [REDACTED]. ukryj [REDACTED] i Ewentualnie [REDACTED]."


def test_expands_partial_model_spans_to_full_words() -> None:
    redactor = Redactor(
        detector=StaticDetector(
            [
                Span(8, 23, "ORGANIZATION_NAME"),
                Span(38, 40, "PERSON_NAME"),
            ]
        )
    )

    text = "Albo do Stefy Marketingu. Ewentualnie paweł kowalski ci powie co i jak."
    result = redactor.redact_text(text)

    assert result == "Albo do [REDACTED]. Ewentualnie [REDACTED] kowalski ci powie co i jak."


def test_can_exclude_entity_labels_from_redaction() -> None:
    redactor = Redactor(
        detector=StaticDetector(
            [
                Span(10, 20, "ORGANIZATION_NAME"),
                Span(25, 35, "PERSON_NAME"),
            ]
        ),
        exclude_labels={"ORGANIZATION_NAME"},
    )

    text = "Send to Biegun KLM and Jan Kowalski."
    result = redactor.redact_text(text)

    assert result == "Send to Biegun KLM and [REDACTED]."
