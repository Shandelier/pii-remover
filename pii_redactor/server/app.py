from __future__ import annotations

import os
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from pii_redactor.core.detectors import build_detector
from pii_redactor.core.redactor import Redactor
from pii_redactor.llm import DemoLlmProvider, build_llm_provider
from pii_redactor.store import JsonlStore


class RedactRequest(BaseModel):
    data: Any


class DetectRequest(BaseModel):
    text: str


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1)


def create_app() -> FastAPI:
    detector_backend = os.getenv("PII_DETECTOR_BACKEND", "regex")
    threshold = float(os.getenv("PII_THRESHOLD", "0.5"))
    store_path = os.getenv("PII_STORE_PATH", "data/redacted_logs.jsonl")

    redactor = Redactor(detector=build_detector(backend=detector_backend, threshold=threshold))
    llm_provider = build_llm_provider()
    store = JsonlStore(store_path)

    app = FastAPI(title="PII Redactor Prototype")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "detector_backend": detector_backend}

    @app.post("/detect")
    async def detect(request: DetectRequest) -> dict[str, Any]:
        return {"spans": [asdict(span) for span in redactor.detect(request.text)]}

    @app.post("/redact")
    async def redact(request: RedactRequest) -> dict[str, Any]:
        return {"data": redactor.redact(request.data)}

    @app.post("/chat")
    async def chat(request: ChatRequest) -> dict[str, Any]:
        raw_response = await llm_provider.complete(request.prompt)
        redacted_prompt = redactor.redact_text(request.prompt)
        redacted_response = redactor.redact_text(raw_response)
        provider_name = "demo" if isinstance(llm_provider, DemoLlmProvider) else "openrouter"
        trace = store.append(redacted_prompt, redacted_response, provider_name)
        return {
            "response": raw_response,
            "stored_trace": asdict(trace),
        }

    @app.get("/traces")
    async def traces() -> dict[str, Any]:
        return {"traces": [asdict(trace) for trace in store.list()]}

    return app


app = create_app()
