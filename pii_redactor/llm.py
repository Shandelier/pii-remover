from __future__ import annotations

import os

import httpx


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
        model: str = "openai/gpt-4o-mini",
        base_url: str = "https://openrouter.ai/api/v1",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def complete(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            payload = response.json()
            return payload["choices"][0]["message"]["content"]


def build_llm_provider() -> LlmProvider:
    provider = os.getenv("PII_LLM_PROVIDER", "auto").lower()
    if provider == "demo":
        return DemoLlmProvider()

    api_key = os.getenv("OPENROUTER_API_KEY")
    if provider == "openrouter" and not api_key:
        raise RuntimeError("PII_LLM_PROVIDER=openrouter requires OPENROUTER_API_KEY.")
    if api_key:
        return OpenRouterProvider(api_key=api_key, model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"))
    return DemoLlmProvider()
