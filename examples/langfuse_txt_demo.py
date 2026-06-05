from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from examples.support.llm import DemoLlmProvider, GroqProvider, OpenRouterProvider, build_llm_provider
from pii_redactor.integrations.langfuse import make_mask


DEFAULT_TEXT_FILES = [
    Path("tests/35-examples-PL-lang.txt"),
    Path("tests/35-examples-EN-ES-FR-lang.txt"),
]

TASK_TEMPLATE = """Rewrite the text below exactly line by line. Append " | checked" to the end of every non-empty line. Do not change any content before the appended text.

TEXT:
{text}"""


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


def _known_values(text: str) -> list[str]:
    values = []
    for line in text.splitlines():
        if not (line.startswith("1. ") or line.startswith("2. ") or line.startswith("3. ")):
            continue
        value = line[3:].strip()
        if ": " in value:
            value = value.split(": ", 1)[1].strip()
        values.append(value.rstrip("."))
    return values


def _verify_mask(mask, payload: dict[str, Any], known_values: list[str]) -> dict[str, Any]:
    masked = mask(payload)
    masked_text = f"{masked['input']}\n{masked['output']}"
    leaked_values = [value for value in known_values if value and value in masked_text]
    return {
        "redacted_input_count": masked["input"].count("[REDACTED]"),
        "redacted_output_count": masked["output"].count("[REDACTED]"),
        "known_raw_left": leaked_values,
    }


async def _build_event(path: Path) -> dict[str, Any]:
    provider = build_llm_provider()
    text = path.read_text()
    prompt = TASK_TEMPLATE.format(text=text)
    output = await _complete_by_sections(provider, text) if _use_section_mode(provider) else await provider.complete(prompt)
    model = provider.model if isinstance(provider, (GroqProvider, OpenRouterProvider)) else "demo-llm"
    return {
        "name": f"pii-redactor-txt-{path.stem}",
        "model": model,
        "input": prompt,
        "output": output,
        "metadata": {
            "demo": "txt-long-example",
            "source_file": path.name,
            "chars": len(text),
            "provider": _provider_name(provider),
        },
        "known_values": _known_values(text),
    }


def _provider_name(provider) -> str:
    if isinstance(provider, DemoLlmProvider):
        return "demo"
    if isinstance(provider, GroqProvider):
        return "groq"
    if isinstance(provider, OpenRouterProvider):
        return "openrouter"
    return "unknown"


def _use_section_mode(provider) -> bool:
    if os.getenv("TXT_DEMO_SECTION_MODE"):
        return os.getenv("TXT_DEMO_SECTION_MODE", "").lower() in {"1", "true", "yes"}
    return not isinstance(provider, GroqProvider)


def _split_sections(text: str) -> list[str]:
    sections = []
    current = []
    for line in text.splitlines():
        if line.strip().endswith(":") and line.strip()[:-1].isupper() and current:
            sections.append("\n".join(current))
            current = []
        current.append(line)
    if current:
        sections.append("\n".join(current))
    return sections


async def _complete_by_sections(provider, text: str) -> str:
    concurrency = int(os.getenv("TXT_DEMO_CONCURRENCY", "4"))
    semaphore = asyncio.Semaphore(concurrency)

    async def complete(section: str) -> str:
        async with semaphore:
            output = await provider.complete(TASK_TEMPLATE.format(text=section))
            delay = float(os.getenv("TXT_DEMO_SECTION_DELAY", "0"))
            if delay:
                await asyncio.sleep(delay)
            return output

    outputs = await asyncio.gather(*(complete(section) for section in _split_sections(text)))
    return "\n\n".join(outputs)


async def run(paths: list[Path], dry_run: bool = False, allow_leaks: bool = False) -> None:
    load_dotenv(dotenv_path=Path(".env"))
    os.environ.setdefault("LLM_MAX_TOKENS", "3500")

    mask = make_mask()
    langfuse = None if dry_run else _build_langfuse(mask)
    results = []

    for path in paths:
        event = await _build_event(path)
        payload = {
            "input": event["input"],
            "output": event["output"],
            "metadata": event["metadata"],
        }
        report = _verify_mask(mask, payload, event["known_values"])
        result = {
            "file": path.name,
            "model": event["model"],
            **report,
            "trace_id": None,
            "url": None,
            "skipped_langfuse": False,
        }

        if langfuse is not None and report["known_raw_left"] and not allow_leaks:
            result["skipped_langfuse"] = True

        if langfuse is not None and not result["skipped_langfuse"]:
            with langfuse.start_as_current_observation(
                as_type="generation",
                name=event["name"],
                model=event["model"],
                input=event["input"],
                metadata=event["metadata"],
            ) as generation:
                generation.update(output=event["output"])
                trace_id = langfuse.get_current_trace_id()
                result["trace_id"] = trace_id
                result["url"] = langfuse.get_trace_url(trace_id=trace_id) if trace_id else None

        results.append(result)
        delay = float(os.getenv("TXT_DEMO_FILE_DELAY", "0"))
        if delay:
            await asyncio.sleep(delay)

    if langfuse is not None:
        langfuse.flush()

    for result in results:
        print(f"- {result['file']}")
        print(f"  model: {result['model']}")
        print(f"  redacted_input_count: {result['redacted_input_count']}")
        print(f"  redacted_output_count: {result['redacted_output_count']}")
        print(f"  known_raw_left: {len(result['known_raw_left'])}")
        if result["known_raw_left"]:
            for value in result["known_raw_left"][:10]:
                print(f"    - {value}")
        if result["skipped_langfuse"]:
            print("  skipped_langfuse: true")
        if result["trace_id"]:
            print(f"  trace_id: {result['trace_id']}")
        if result["url"]:
            print(f"  url: {result['url']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Send long TXT examples through OpenRouter and masked Langfuse tracing.")
    parser.add_argument("--dry-run", action="store_true", help="Run the LLM and local mask verification without sending to Langfuse.")
    parser.add_argument("--allow-leaks", action="store_true", help="Send to Langfuse even if local verification finds known raw values after masking.")
    parser.add_argument("paths", nargs="*", type=Path, default=DEFAULT_TEXT_FILES)
    args = parser.parse_args()
    asyncio.run(run(args.paths, dry_run=args.dry_run, allow_leaks=args.allow_leaks))


if __name__ == "__main__":
    main()
