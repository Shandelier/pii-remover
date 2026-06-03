from pii_redactor.integrations.langfuse import make_mask


def test_make_mask_matches_langfuse_mask_contract() -> None:
    mask = make_mask()

    assert mask("Email: jan.kowalski@example.com") == "Email: [REDACTED]"
    assert mask({"metadata": {"customer_contact": "+48 501 222 333"}}) == {
        "metadata": {"customer_contact": "[REDACTED]"}
    }


def test_make_mask_reads_backend_env(monkeypatch) -> None:
    monkeypatch.setenv("PII_DETECTOR_BACKEND", "regex")

    mask = make_mask()

    assert mask("PESEL 85010112345") == "PESEL [REDACTED]"
