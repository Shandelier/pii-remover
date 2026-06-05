from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pii_redactor.core.detectors import build_detector
from pii_redactor.core.redactor import Redactor
from examples.support.llm import DemoLlmProvider, build_llm_provider
from examples.support.store import JsonlStore


DEMO_PROMPTS = [
    "Nazywam się Jan Kowalski, PESEL 85010112345, email jan.kowalski@example.com. Opisz ryzyko przetwarzania takich danych.",
    "Pacjentka Anna Nowak mieszka przy ul. Długa 12/4 w Krakowie, telefon +48 501 222 333. Przygotuj krótką odpowiedź supportu.",
    "Karta klienta: 4111 1111 1111 1111, IP 192.168.1.20, IBAN PL61 1090 1014 0000 0712 1981 2874. Napisz neutralne podsumowanie.",
]


async def run_demo() -> list[dict[str, str]]:
    store_path = Path(os.getenv("PII_STORE_PATH", "data/demo_redacted_logs.jsonl"))
    if store_path.exists():
        store_path.unlink()

    redactor = Redactor(detector=build_detector(os.getenv("PII_DETECTOR_BACKEND", "local")))
    provider = build_llm_provider()
    store = JsonlStore(store_path)
    provider_name = "demo" if isinstance(provider, DemoLlmProvider) else "openrouter"

    results = []
    for prompt in DEMO_PROMPTS:
        raw_response = await provider.complete(prompt)
        redacted_prompt = redactor.redact_text(prompt)
        redacted_response = redactor.redact_text(raw_response)
        trace = store.append(redacted_prompt, redacted_response, provider_name)
        results.append(
            {
                "input_prompt": prompt,
                "llm_response": raw_response,
                "stored_prompt": trace.redacted_prompt,
                "stored_response": trace.redacted_response,
            }
        )
    return results


def main() -> None:
    results = asyncio.run(run_demo())
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print("\nStored only redacted traces in data/demo_redacted_logs.jsonl")


if __name__ == "__main__":
    main()
