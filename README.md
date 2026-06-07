# any-lang-anonymizer

Drop-in PII redaction for teams that already use Langfuse.

```bash
pip install any-lang-anonymizer
```

```python
from langfuse import Langfuse
from pii_redactor.integrations.langfuse import make_mask

langfuse = Langfuse(mask=make_mask())
```

That is the main API. `make_mask()` recursively scans every string Langfuse sends through the mask callback, including nested `input`, `output`, `metadata`, `messages`, tool calls, and custom fields.

## Supported Integrations

| Framework | Status | How to use |
| --- | --- | --- |
| Langfuse SDK | Ready | `Langfuse(mask=make_mask())` |
| LangChain / LangGraph | Ready | `make_langfuse_callback()` with `config={"callbacks": [...]}` |
| Pydantic AI | Coming soon | Planned example |
| OpenAI SDK | Coming soon | Planned example |

## How It Works

`any-lang-anonymizer` runs the Bards AI ONNX PII model locally. Raw observability data is redacted in your app before it is sent to Langfuse.

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

## LangChain / LangGraph

Langfuse traces LangChain and LangGraph through a callback handler. Use the same callback, but create the Langfuse client with the anonymizer mask first.

```bash
pip install 'any-lang-anonymizer[langchain]'
```

```python
from langchain.agents import create_agent
from pii_redactor.integrations.langchain import make_langfuse_callback

langfuse_handler = make_langfuse_callback()
agent = create_agent(model="groq:llama-3.1-8b-instant", tools=[])

agent.invoke(
    {"messages": [{"role": "user", "content": "Jan Kowalski, jan.kowalski@example.com"}]},
    config={"callbacks": [langfuse_handler]},
)
```

`create_agent` runs on LangGraph internally, so this is the shortest LangGraph-backed agent path. A runnable example is in `examples/langchain_langgraph_langfuse.py`.

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
