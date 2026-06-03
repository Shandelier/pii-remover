## Repo Notes

- User wants short, blunt answers in Polish unless context suggests otherwise; explain behavior/user impact before implementation detail.
- Current MVP goal: make a working self-hosted PII redaction step for Langfuse-style LLM observability logs, not a hosted storage product.
- Architecture preference: raw PII may go to the user's own LLM provider path, but observability/storage must only receive redacted prompt/response.
- Prototype should run without external keys; optional OpenRouter is useful, but local deterministic demo fallback is required.
- Gotcha from demo: LLM responses can reintroduce or inflect PII (for example "Pani Anno"), so always redact both prompt and response immediately before storage.
- For Langfuse examples, keep a dry-run path so the demo works without a self-hosted Langfuse instance or credentials.
