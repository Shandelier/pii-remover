from pii_redactor.integrations.langfuse import make_mask
from pii_redactor.core.types import Span


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


def patch_detector(monkeypatch) -> None:
    monkeypatch.setattr(
        "pii_redactor.integrations.langfuse.build_detector",
        lambda *_args, **_kwargs: PatternDetector(
            {
                "jan.kowalski@example.com": "EMAIL",
                "+48 501 222 333": "PHONE_NUMBER",
                "85010112345": "PERSONAL_ID",
            }
        ),
    )


def test_make_mask_matches_langfuse_mask_contract(monkeypatch) -> None:
    patch_detector(monkeypatch)
    mask = make_mask()

    assert mask("Email: jan.kowalski@example.com") == "Email: [REDACTED]"
    assert mask({"metadata": {"customer_contact": "+48 501 222 333"}}) == {
        "metadata": {"customer_contact": "[REDACTED]"}
    }


def test_make_mask_reads_backend_env(monkeypatch) -> None:
    patch_detector(monkeypatch)
    monkeypatch.setenv("PII_DETECTOR_BACKEND", "local")

    mask = make_mask()

    assert mask("PESEL 85010112345") == "PESEL [REDACTED]"


def test_make_mask_reads_excluded_labels_env(monkeypatch) -> None:
    patch_detector(monkeypatch)
    monkeypatch.setenv("PII_EXCLUDE_LABELS", "EMAIL")

    mask = make_mask()

    assert mask("Email: jan.kowalski@example.com") == "Email: jan.kowalski@example.com"


def test_make_mask_can_limit_and_exclude_paths(monkeypatch) -> None:
    patch_detector(monkeypatch)

    mask = make_mask(include_paths=["messages.*.content", "metadata"], exclude_paths=["metadata.support_contact"])

    assert mask(
        {
            "messages": [{"content": "Email: jan.kowalski@example.com"}],
            "metadata": {
                "customer_contact": "+48 501 222 333",
                "support_contact": "jan.kowalski@example.com",
            },
        }
    ) == {
        "messages": [{"content": "Email: [REDACTED]"}],
        "metadata": {
            "customer_contact": "[REDACTED]",
            "support_contact": "jan.kowalski@example.com",
        },
    }


def test_make_mask_reads_paths_env(monkeypatch) -> None:
    patch_detector(monkeypatch)
    monkeypatch.setenv("PII_INCLUDE_PATHS", "input,metadata")
    monkeypatch.setenv("PII_EXCLUDE_PATHS", "metadata.support_contact")

    mask = make_mask()

    assert mask(
        {
            "input": "Email: jan.kowalski@example.com",
            "output": "Email: jan.kowalski@example.com",
            "metadata": {"support_contact": "+48 501 222 333"},
        }
    ) == {
        "input": "Email: [REDACTED]",
        "output": "Email: jan.kowalski@example.com",
        "metadata": {"support_contact": "+48 501 222 333"},
    }
