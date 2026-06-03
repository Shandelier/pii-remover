from pii_redactor.core.redactor import Redactor


def test_redacts_nested_json() -> None:
    redactor = Redactor()

    result = redactor.redact(
        {
            "input": "Jan Kowalski ma email jan.kowalski@example.com i PESEL 85010112345.",
            "metadata": {"phone": "+48 501 222 333"},
        }
    )

    assert result["input"] == "[REDACTED] ma email [REDACTED] i PESEL [REDACTED]."
    assert result["metadata"]["phone"] == "[REDACTED]"


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
