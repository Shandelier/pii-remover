from fastapi.testclient import TestClient

from pii_redactor.core.types import Span
from playground import app as server_app


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
        server_app,
        "build_detector",
        lambda *_args, **_kwargs: PatternDetector(
            {
                "Marta Nowak": "PERSON_NAME",
                "marta.nowak@example.com": "EMAIL",
                "+48 600 700 800": "PHONE_NUMBER",
                "Jan Kowalski": "PERSON_NAME",
                "jan.kowalski@example.com": "EMAIL",
                "85010112345": "PERSONAL_ID",
            }
        ),
    )


def test_chat_stores_redacted_trace(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PII_STORE_PATH", str(tmp_path / "logs.jsonl"))
    monkeypatch.setenv("PII_LLM_PROVIDER", "demo")
    patch_detector(monkeypatch)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    client = TestClient(server_app.create_app())

    response = client.post(
        "/chat",
        json={"prompt": "Marta Nowak, email marta.nowak@example.com, telefon +48 600 700 800."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "marta.nowak@example.com" in payload["response"]
    assert "marta.nowak@example.com" not in payload["stored_trace"]["redacted_prompt"]
    assert "marta.nowak@example.com" not in payload["stored_trace"]["redacted_response"]


def test_playground_serves_html() -> None:
    client = TestClient(server_app.create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "PII Redactor Playground" in response.text
    assert 'fetch("/redact"' in response.text
    assert 'fetch("/detect"' in response.text
    assert 'fetch("/health"' in response.text
    assert "contenteditable" in response.text
    assert "data-prediction" in response.text
    assert 'id="tooltip"' in response.text
    assert "Detector: loading..." in response.text


def test_playground_alias_still_works() -> None:
    client = TestClient(server_app.create_app())

    response = client.get("/playground")

    assert response.status_code == 200
    assert "PII Redactor Playground" in response.text


def test_detect_returns_spans_for_highlighting(monkeypatch) -> None:
    patch_detector(monkeypatch)
    client = TestClient(server_app.create_app())

    response = client.post("/detect", json={"text": "Jan Kowalski ma email jan.kowalski@example.com i PESEL 85010112345."})

    assert response.status_code == 200
    spans = response.json()["spans"]
    assert {"start": 0, "end": 12, "label": "PERSON_NAME", "score": 1.0} in spans
    assert any(span["label"] == "EMAIL" for span in spans)
    assert any(span["label"] == "PERSONAL_ID" for span in spans)


def test_redact_uses_bards_detector(monkeypatch) -> None:
    patch_detector(monkeypatch)
    client = TestClient(server_app.create_app())

    response = client.post(
        "/redact",
        json={"data": "Jan Kowalski ma email jan.kowalski@example.com."},
    )

    assert response.status_code == 200
    assert response.json()["data"] == "[REDACTED] ma email [REDACTED]."
