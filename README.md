# pii-redactor

Drop-in PII redaction for teams that already use Langfuse.

The main path is client-side Langfuse masking: data is redacted in the user's app before Langfuse receives traced `input`, `output`, and `metadata`.

## Add To Existing Langfuse Code

Before:

```python
from langfuse import Langfuse

langfuse = Langfuse()
```

After:

```python
from langfuse import Langfuse
from pii_redactor.integrations.langfuse import make_mask

langfuse = Langfuse(mask=make_mask())
```

For the Bards AI local model backend:

```bash
python3 -m pip install -e '.[local]'
```

```python
langfuse = Langfuse(mask=make_mask(backend="local"))
```

The default prototype backend is regex-based so the examples run immediately. `backend="local"` is wired for `bardsai/eu-pii-anonimization-multilang`.

## Langfuse Demo

Dry-run Langfuse-shaped generation events without sending anything:

```bash
PII_LLM_PROVIDER=demo python3 examples/langfuse_demo.py
```

Send masked events to Langfuse:

```bash
python3 -m pip install -e '.[langfuse]'
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
export LANGFUSE_BASE_URL=http://localhost:3000
PII_LLM_PROVIDER=demo python3 examples/langfuse_demo.py
```

The demo uses three PII-heavy prompts and masks the traced prompt, LLM response, and metadata before Langfuse export.

## Minimal Existing-App Example

See [examples/langfuse_existing_app.py](examples/langfuse_existing_app.py).

The whole integration is intentionally just the Langfuse `mask` callback. Langfuse documents that this callback is applied to observation `input`, `output`, and `metadata` before export: [Langfuse masking docs](https://langfuse.com/docs/observability/features/masking).

## Optional Server Prototype

The FastAPI server is a secondary path for teams that want a standalone gateway.

```bash
python3 -m pip install -e .
python3 -m uvicorn pii_redactor.server.app:app --reload
```

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Jan Kowalski, email jan.kowalski@example.com, PESEL 85010112345. Odpowiedz krótko."}'
```

Stored traces are written only after redaction:

```bash
curl http://127.0.0.1:8000/traces
```

## Local Demo Store

```bash
PII_LLM_PROVIDER=demo python3 examples/demo.py
```

This writes redacted traces to:

```text
data/demo_redacted_logs.jsonl
```

If `OPENROUTER_API_KEY` is set, demos use OpenRouter. Force local demo mode with `PII_LLM_PROVIDER=demo`.
