from pii_redactor.core.redactor import Redactor


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
