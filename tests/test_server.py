from fastapi.testclient import TestClient

from pii_redactor.server.app import create_app


def test_chat_stores_redacted_trace(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PII_STORE_PATH", str(tmp_path / "logs.jsonl"))
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = TestClient(create_app())

    response = client.post(
        "/chat",
        json={"prompt": "Marta Nowak, email marta.nowak@example.com, telefon +48 600 700 800."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "marta.nowak@example.com" in payload["response"]
    assert "marta.nowak@example.com" not in payload["stored_trace"]["redacted_prompt"]
    assert "marta.nowak@example.com" not in payload["stored_trace"]["redacted_response"]
