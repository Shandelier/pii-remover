from __future__ import annotations

import asyncio
import os

import httpx

DEFAULT_OPENROUTER_MODEL = "liquid/lfm-2.5-1.2b-thinking:free"
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"


class LlmProvider:
    async def complete(self, prompt: str) -> str:
        raise NotImplementedError


class DemoLlmProvider(LlmProvider):
    async def complete(self, prompt: str) -> str:
        return (
            "Demo odpowiedz LLM: rozumiem zgloszenie. W odpowiedzi nie powinienem utrwalac danych "
            f"takich jak te z prompta: {prompt}"
        )


class OpenRouterProvider(LlmProvider):
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_OPENROUTER_MODEL,
        base_url: str = "https://openrouter.ai/api/v1",
        max_tokens: int | None = None,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.max_retries = max_retries

    async def complete(self, prompt: str) -> str:
        payload: dict[str, object] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens

        async with httpx.AsyncClient(timeout=60) as client:
            for attempt in range(self.max_retries + 1):
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                if response.status_code not in {429, 500, 502, 503, 504} or attempt == self.max_retries:
                    response.raise_for_status()
                    response_payload = response.json()
                    return response_payload["choices"][0]["message"]["content"]
                retry_after = response.headers.get("retry-after")
                await asyncio.sleep(float(retry_after) if retry_after else 2**attempt)

        raise RuntimeError("OpenRouter request failed.")


class GroqProvider(LlmProvider):
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_GROQ_MODEL,
        base_url: str = "https://api.groq.com/openai/v1",
        max_tokens: int | None = None,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.max_retries = max_retries

    async def complete(self, prompt: str) -> str:
        payload: dict[str, object] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens

        async with httpx.AsyncClient(timeout=60) as client:
            for attempt in range(self.max_retries + 1):
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                if response.status_code not in {429, 500, 502, 503, 504} or attempt == self.max_retries:
                    response.raise_for_status()
                    response_payload = response.json()
                    return response_payload["choices"][0]["message"]["content"]
                retry_after = response.headers.get("retry-after")
                await asyncio.sleep(float(retry_after) if retry_after else 2**attempt)

        raise RuntimeError("Groq request failed.")


def build_llm_provider() -> LlmProvider:
    provider = os.getenv("PII_LLM_PROVIDER", "auto").lower()
    if provider == "demo":
        return DemoLlmProvider()

    groq_api_key = os.getenv("GROQ_API_KEY")
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    max_tokens = os.getenv("LLM_MAX_TOKENS") or os.getenv("OPENROUTER_MAX_TOKENS")
    max_retries = os.getenv("LLM_MAX_RETRIES") or os.getenv("OPENROUTER_MAX_RETRIES")

    if provider == "groq" and not groq_api_key:
        raise RuntimeError("PII_LLM_PROVIDER=groq requires GROQ_API_KEY.")
    if provider == "openrouter" and not openrouter_api_key:
        raise RuntimeError("PII_LLM_PROVIDER=openrouter requires OPENROUTER_API_KEY.")

    if provider == "groq" or (provider == "auto" and groq_api_key):
        return GroqProvider(
            api_key=groq_api_key or "",
            model=os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL),
            max_tokens=int(max_tokens) if max_tokens else None,
            max_retries=int(max_retries) if max_retries else 3,
        )
    if provider == "openrouter" or (provider == "auto" and openrouter_api_key):
        return OpenRouterProvider(
            api_key=openrouter_api_key or "",
            model=os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL),
            max_tokens=int(max_tokens) if max_tokens else None,
            max_retries=int(max_retries) if max_retries else 3,
        )
    return DemoLlmProvider()
