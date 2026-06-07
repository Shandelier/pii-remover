from pii_redactor.core.redactor import Redactor
from pii_redactor.core.types import Span


class StaticDetector:
    def __init__(self, spans: list[Span]) -> None:
        self.spans = spans

    def detect(self, text: str) -> list[Span]:
        return self.spans


class PatternDetector:
    def __init__(self, patterns: dict[str, str]) -> None:
        self.patterns = patterns

    def detect(self, text: str) -> list[Span]:
        spans = []
        for value, label in self.patterns.items():
            start = text.find(value)
            if start >= 0:
                spans.append(Span(start, start + len(value), label, 1.0))
        return spans


def test_redacts_langfuse_shaped_trace_payload() -> None:
    redactor = Redactor(
        detector=PatternDetector(
            {
                "Jan Kowalski": "PERSON_NAME",
                "jan.kowalski@example.com": "EMAIL",
                "85010112345": "PERSONAL_ID",
                "Jana Kowalskiego": "PERSON_NAME",
                "+48 501 222 333": "PHONE_NUMBER",
            }
        )
    )

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
    from examples.support.store import JsonlStore

    store = JsonlStore(tmp_path / "logs.jsonl")
    store.append("[REDACTED]", "Odpowiedz dla [REDACTED]", "demo")

    content = (tmp_path / "logs.jsonl").read_text()
    assert "[REDACTED]" in content
    assert "jan.kowalski@example.com" not in content


def test_redacts_simple_polish_vocative_name() -> None:
    redactor = Redactor(detector=PatternDetector({"Pani Anno": "PERSON_NAME"}))

    result = redactor.redact_text("Szanowna Pani Anno, proszę o kontakt.")

    assert result == "Szanowna [REDACTED], proszę o kontakt."


def test_redacts_common_free_form_names_from_playground_text() -> None:
    redactor = Redactor(
        detector=PatternDetector(
            {
                "James": "PERSON_NAME",
                "James Bond": "PERSON_NAME",
                "Kowalski Jerzy": "PERSON_NAME",
                "jerzy": "PERSON_NAME",
                "paweł kowalski": "PERSON_NAME",
            }
        )
    )

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


def test_spans_for_text_returns_expanded_spans() -> None:
    redactor = Redactor(detector=StaticDetector([Span(8, 23, "ORGANIZATION_NAME")]))

    text = "Albo do Stefy Marketingu."
    result = redactor.spans_for_text(text)

    assert result == [Span(8, 24, "ORGANIZATION_NAME")]


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


def test_redacts_nested_observability_payload_by_default() -> None:
    redactor = Redactor(
        detector=PatternDetector(
            {
                "jan.kowalski@example.com": "EMAIL",
                "Anna Nowak": "PERSON_NAME",
                "+48 501 222 333": "PHONE_NUMBER",
            }
        )
    )

    result = redactor.redact(
        {
            "input": {"messages": [{"role": "user", "content": "Email jan.kowalski@example.com"}]},
            "output": {"reasoning": "Call Anna Nowak"},
            "tool_calls": [{"name": "send_sms", "args": {"phone": "+48 501 222 333"}}],
            "usage": {"total_tokens": 123},
        }
    )

    assert result["input"]["messages"][0]["content"] == "Email [REDACTED]"
    assert result["output"]["reasoning"] == "Call [REDACTED]"
    assert result["tool_calls"][0]["args"]["phone"] == "[REDACTED]"
    assert result["usage"]["total_tokens"] == 123


def test_redacts_pydantic_style_message_objects() -> None:
    class Message:
        def __init__(self, content: str) -> None:
            self.content = content

        def model_dump(self, mode: str = "python") -> dict[str, str]:
            return {"type": "human", "content": self.content, "mode": mode}

    redactor = Redactor(detector=PatternDetector({"jan.kowalski@example.com": "EMAIL"}))

    result = redactor.redact({"messages": [Message("Email jan.kowalski@example.com")]})

    assert result["messages"][0]["content"] == "Email [REDACTED]"
    assert result["messages"][0]["mode"] == "json"


def test_include_paths_limits_which_fields_are_scanned() -> None:
    redactor = Redactor(
        detector=PatternDetector(
            {
                "jan.kowalski@example.com": "EMAIL",
                "ops@example.com": "EMAIL",
            }
        ),
        include_paths=["messages.*.content"],
    )

    result = redactor.redact(
        {
            "messages": [{"role": "user", "content": "Email jan.kowalski@example.com"}],
            "metadata": {"support_contact": "ops@example.com"},
        }
    )

    assert result["messages"][0]["content"] == "Email [REDACTED]"
    assert result["metadata"]["support_contact"] == "ops@example.com"


def test_exclude_paths_win_over_include_paths() -> None:
    redactor = Redactor(
        detector=PatternDetector(
            {
                "jan.kowalski@example.com": "EMAIL",
                "ops@example.com": "EMAIL",
            }
        ),
        include_paths=["metadata"],
        exclude_paths=["metadata.support_contact"],
    )

    result = redactor.redact(
        {
            "metadata": {
                "customer_email": "jan.kowalski@example.com",
                "support_contact": "ops@example.com",
            }
        }
    )

    assert result["metadata"]["customer_email"] == "[REDACTED]"
    assert result["metadata"]["support_contact"] == "ops@example.com"
