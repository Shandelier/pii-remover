from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.demo import DEMO_PROMPTS
from pii_redactor.integrations.langfuse import make_mask
from pii_redactor.llm import DemoLlmProvider, build_llm_provider


def _has_langfuse_config() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


async def _build_events() -> list[dict[str, Any]]:
    provider = build_llm_provider()
    provider_name = "demo" if isinstance(provider, DemoLlmProvider) else "openrouter"

    events = []
    for index, prompt in enumerate(DEMO_PROMPTS, start=1):
        response = await provider.complete(prompt)
        events.append(
            {
                "name": f"pii-redactor-demo-{index}",
                "model": os.getenv("OPENROUTER_MODEL", provider_name),
                "input": prompt,
                "output": response,
                "metadata": {
                    "demo": "langfuse-mask",
                    "case": index,
                    "support_contact": "ops@example.com",
                },
            }
        )
    return events


def _send_to_langfuse(events: list[dict[str, Any]]) -> None:
    try:
        from langfuse import Langfuse
    except ImportError as exc:
        raise RuntimeError("Install Langfuse demo dependencies with `python3 -m pip install -e '.[langfuse]'`.") from exc

    langfuse = Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        base_url=os.getenv("LANGFUSE_BASE_URL"),
        mask=make_mask(),
    )

    for event in events:
        with langfuse.start_as_current_observation(
            as_type="generation",
            name=event["name"],
            model=event["model"],
            input=event["input"],
            metadata=event["metadata"],
        ) as generation:
            generation.update(output=event["output"])

    langfuse.flush()


def _print_dry_run(events: list[dict[str, Any]]) -> None:
    mask = make_mask()
    masked_events = [
        {
            **event,
            "input": mask(event["input"]),
            "output": mask(event["output"]),
            "metadata": mask(event["metadata"]),
        }
        for event in events
    ]
    print(json.dumps(masked_events, ensure_ascii=False, indent=2))
    print("\nDry run only. Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to send these masked events to Langfuse.")


async def run() -> None:
    events = await _build_events()
    if _has_langfuse_config():
        _send_to_langfuse(events)
        print(f"Sent {len(events)} masked generation events to Langfuse.")
        return

    _print_dry_run(events)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
