from examples.support.llm import DEFAULT_GROQ_MODEL, DEFAULT_OPENROUTER_MODEL, GroqProvider, OpenRouterProvider, build_llm_provider


def test_groq_provider_is_used_by_default_when_key_exists(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    provider = build_llm_provider()

    assert isinstance(provider, GroqProvider)
    assert provider.model == DEFAULT_GROQ_MODEL


def test_groq_model_can_be_overridden(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    provider = build_llm_provider()

    assert isinstance(provider, GroqProvider)
    assert provider.model == "llama-3.3-70b-versatile"


def test_openrouter_provider_uses_free_model_by_default(monkeypatch) -> None:
    monkeypatch.setenv("PII_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)

    provider = build_llm_provider()

    assert isinstance(provider, OpenRouterProvider)
    assert provider.model == DEFAULT_OPENROUTER_MODEL


def test_openrouter_model_can_be_overridden(monkeypatch) -> None:
    monkeypatch.setenv("PII_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    provider = build_llm_provider()

    assert isinstance(provider, OpenRouterProvider)
    assert provider.model == "openai/gpt-4o-mini"


def test_openrouter_max_tokens_can_be_configured(monkeypatch) -> None:
    monkeypatch.setenv("PII_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MAX_TOKENS", "4096")

    provider = build_llm_provider()

    assert isinstance(provider, OpenRouterProvider)
    assert provider.max_tokens == 4096


def test_explicit_openrouter_wins_over_groq_key(monkeypatch) -> None:
    monkeypatch.setenv("PII_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")

    provider = build_llm_provider()

    assert isinstance(provider, OpenRouterProvider)
