# pii-redactor

Drop-in PII redaction for teams that already use Langfuse.

```bash
pip install langfuse-pii-redactor
```

```python
from langfuse import Langfuse
from pii_redactor.integrations.langfuse import make_mask

langfuse = Langfuse(mask=make_mask())
```

That is the main API. `make_mask()` recursively scans every string Langfuse sends through the mask callback, including nested `input`, `output`, `metadata`, `messages`, tool calls, and custom fields.

## How It Works

`pii-redactor` runs the Bards AI ONNX PII model locally. Raw observability data is redacted in your app before it is sent to Langfuse.

The model is downloaded from Hugging Face on first use and cached locally by `huggingface-hub`.

Optional model config:

```bash
export PII_MODEL_ID=bardsai/eu-pii-anonimization-multilang
export PII_MODEL_CACHE_DIR=/path/to/model-cache
```

You can narrow or exclude JSON paths if needed:

```python
langfuse = Langfuse(
    mask=make_mask(
        include_paths=["input", "output", "metadata", "messages.*.content", "tool_calls.*.args"],
        exclude_paths=["metadata.trace_id", "metadata.model", "usage"],
    )
)
```

By default, no path config is needed. Everything text-like is scanned.

## Model

The default model is [`bardsai/eu-pii-anonimization-multilang`](https://huggingface.co/bardsai/eu-pii-anonimization-multilang). The project is Apache-2.0 licensed, matching the model license. The model files are not bundled in this package.

## Local Playground

The FastAPI playground is a demo tool, not part of the core library.

```bash
python3 -m pip install -e '.[server]'
python3 -m uvicorn playground.app:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Examples

Runnable demos live in `examples/`.

```bash
python3 -m pip install -e '.[demo]'
PII_LLM_PROVIDER=demo python3 examples/langfuse_demo.py
```

For real LLM demo traces:

```bash
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
export LANGFUSE_BASE_URL=https://cloud.langfuse.com
export GROQ_API_KEY=gsk_...
python3 examples/langfuse_txt_demo.py --allow-leaks
```

The long TXT demo uses Groq `llama-3.1-8b-instant` by default when `GROQ_API_KEY` is set. It asks the LLM to append ` | checked` to each non-empty line, then verifies locally whether known raw values remain after masking.
