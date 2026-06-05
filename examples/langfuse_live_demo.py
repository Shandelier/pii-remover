from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from pii_redactor.integrations.langfuse import make_mask


LIVE_DEMO_EVENTS = [
    {
        "name": "pii-redactor-live-demo-email",
        "model": "demo-llm",
        "input": "Jan Kowalski, PESEL 85010112345, email jan.kowalski@example.com. Napisz krótką odpowiedź supportu.",
        "output": "Szanowny Panie Janie, wyślemy potwierdzenie na jan.kowalski@example.com.",
        "metadata": {
            "demo": "langfuse-live",
            "case": "email-pesel",
            "customer_phone": "+48 501 222 333",
        },
    },
    {
        "name": "pii-redactor-live-demo-payment",
        "model": "demo-llm",
        "input": "Klientka Anna Nowak podała kartę 4111 1111 1111 1111 i IP 192.168.1.20.",
        "output": "Nie zapisuj numeru karty 4111 1111 1111 1111 w notatce CRM.",
        "metadata": {
            "demo": "langfuse-live",
            "case": "payment",
            "billing_iban": "PL61 1090 1014 0000 0712 1981 2874",
        },
    },
    {
        "name": "pii-redactor-live-demo-address",
        "model": "demo-llm",
        "input": "Wyślij paczkę do Marty Wiśniewskiej na ul. Długa 12/4, 31-147 Kraków.",
        "output": "Paczka dla Marty Wiśniewskiej zostanie nadana dzisiaj.",
        "metadata": {
            "demo": "langfuse-live",
            "case": "address",
            "support_contact": "ops@example.com",
        },
    },
]


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing {name}. Add it to .env or export it.")
    return value


def _build_langfuse(mask):
    from langfuse import Langfuse

    base_url = os.getenv("LANGFUSE_BASE_URL") or os.getenv("LANGFUSE_HOST")
    return Langfuse(
        public_key=_required_env("LANGFUSE_PUBLIC_KEY"),
        secret_key=_required_env("LANGFUSE_SECRET_KEY"),
        base_url=base_url,
        mask=mask,
        environment=os.getenv("LANGFUSE_ENVIRONMENT", "pii-redactor-demo"),
        release=os.getenv("LANGFUSE_RELEASE", "local-demo"),
    )


def _redacted_preview(mask, event: dict[str, Any]) -> dict[str, Any]:
    return {
        "input": mask(event["input"]),
        "output": mask(event["output"]),
        "metadata": mask(event["metadata"]),
    }


def run(unsafe_no_mask: bool = False) -> None:
    load_dotenv()

    mask = None if unsafe_no_mask else make_mask()
    langfuse = _build_langfuse(mask)
    links = []

    for event in LIVE_DEMO_EVENTS:
        with langfuse.start_as_current_observation(
            as_type="generation",
            name=event["name"],
            model=event["model"],
            input=event["input"],
            metadata=event["metadata"],
        ) as generation:
            generation.update(output=event["output"])
            trace_id = langfuse.get_current_trace_id()
            observation_id = langfuse.get_current_observation_id()
            links.append(
                {
                    "name": event["name"],
                    "trace_id": trace_id,
                    "observation_id": observation_id,
                    "url": langfuse.get_trace_url(trace_id=trace_id) if trace_id else None,
                    "preview": None if unsafe_no_mask else _redacted_preview(mask, event),
                }
            )

    langfuse.flush()

    print(f"Sent {len(links)} generation events to Langfuse.")
    if unsafe_no_mask:
        print("WARNING: unsafe no-mask mode was used; raw PII was sent.")
    for item in links:
        print(f"- {item['name']}")
        print(f"  trace_id: {item['trace_id']}")
        print(f"  observation_id: {item['observation_id']}")
        if item["url"]:
            print(f"  url: {item['url']}")
        if item["preview"]:
            print(f"  redacted_input: {item['preview']['input']}")
            print(f"  redacted_output: {item['preview']['output']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Send masked PII redaction demo traces to Langfuse.")
    parser.add_argument(
        "--unsafe-no-mask",
        action="store_true",
        help="Send raw PII without the pii-redactor mask. Use only for manual comparison in a private project.",
    )
    args = parser.parse_args()
    run(unsafe_no_mask=args.unsafe_no_mask)


if __name__ == "__main__":
    main()
