# pii-redactor

Self-hosted prototype for adding PII redaction before LLM observability storage.

The demo flow:

1. User sends a prompt containing PII.
2. The server receives it.
3. The prompt is sent to OpenRouter if `OPENROUTER_API_KEY` is set, otherwise to a deterministic demo LLM.
4. The prompt and LLM response are redacted.
5. Only redacted prompt/response are written to `data/*.jsonl`.

## Run the demo

```bash
python3 examples/demo.py
```

The demo runs three PII-heavy prompts and writes only redacted traces to:

```text
data/demo_redacted_logs.jsonl
```

## Run the server

```bash
python3 -m pip install -e .
python3 -m uvicorn pii_redactor.server.app:app --reload
```

Then send a prompt:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Jan Kowalski, email jan.kowalski@example.com, PESEL 85010112345. Odpowiedz krótko."}'
```

Inspect stored redacted traces:

```bash
curl http://127.0.0.1:8000/traces
```

## Optional OpenRouter

```bash
export OPENROUTER_API_KEY=...
export OPENROUTER_MODEL=openai/gpt-4o-mini
python3 examples/demo.py
```

Without a key, the prototype uses a local deterministic demo provider so the flow is still testable.

Force local demo mode even when an OpenRouter key exists:

```bash
PII_LLM_PROVIDER=demo python3 examples/demo.py
```

## Optional Bards AI model backend

The default demo backend is regex-based so it runs immediately. The production-shaped local backend is wired for:

```text
bardsai/eu-pii-anonimization-multilang
```

Install model dependencies and switch backend:

```bash
python3 -m pip install -e '.[local]'
export PII_DETECTOR_BACKEND=local
python3 examples/demo.py
```

## Langfuse-style hook

```python
from pii_redactor.integrations.langfuse import make_mask

langfuse = Langfuse(mask=make_mask(backend="local"))
```

## Langfuse SDK demo

Dry-run the same masking function against Langfuse-shaped generation events:

```bash
PII_LLM_PROVIDER=demo python3 examples/langfuse_demo.py
```

Send to Langfuse:

```bash
python3 -m pip install -e '.[langfuse]'
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
export LANGFUSE_BASE_URL=http://localhost:3000
PII_LLM_PROVIDER=demo python3 examples/langfuse_demo.py
```

The important bit is still the one-liner: `Langfuse(mask=make_mask(...))`. Langfuse applies it to traced input, output, and metadata before export.
