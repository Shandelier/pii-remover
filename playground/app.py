from __future__ import annotations

import os
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from pii_redactor.core.detectors import build_detector
from pii_redactor.core.redactor import Redactor
from examples.support.llm import DemoLlmProvider, build_llm_provider
from examples.support.store import JsonlStore


class RedactRequest(BaseModel):
    data: Any


class DetectRequest(BaseModel):
    text: str


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1)


def _labels_from_env(name: str) -> set[str] | None:
    value = os.getenv(name)
    if not value:
        return None
    return {item.strip() for item in value.split(",") if item.strip()}


def _detector_from_env() -> str:
    backend = os.getenv("PII_DETECTOR_BACKEND", "local").strip() or "local"
    if backend == "bardsai":
        return "local"
    if backend != "local":
        raise ValueError(f"Unsupported detector backend: {backend}")
    return backend


class DetectorRegistry:
    def __init__(
        self,
        threshold: float,
        include_labels: set[str] | None,
        exclude_labels: set[str],
    ) -> None:
        self.threshold = threshold
        self.include_labels = include_labels
        self.exclude_labels = exclude_labels
        self._cache: dict[str, Redactor] = {}

    def redactor_for(self, backend: str) -> Redactor:
        if backend not in self._cache:
            self._cache[backend] = Redactor(
                detector=build_detector(backend, threshold=self.threshold),
                include_labels=self.include_labels,
                exclude_labels=self.exclude_labels,
            )
        return self._cache[backend]


PLAYGROUND_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="icon" href="data:," />
  <title>PII Redactor Playground</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #17202a;
      --muted: #657080;
      --border: #d8dde5;
      --accent: #0f766e;
      --accent-dark: #0b5f59;
      --danger: #b42318;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
    }

    main {
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0;
    }

    header {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 18px;
    }

    .header-copy {
      display: grid;
      gap: 8px;
    }

    .badge {
      width: fit-content;
      border: 1px solid var(--border);
      background: #ffffff;
      color: #344054;
      border-radius: 999px;
      padding: 5px 9px;
      font-size: 12px;
      font-weight: 700;
    }

    .badge.model {
      border-color: #99d6cf;
      color: var(--accent-dark);
      background: #effbf9;
    }

    h1 {
      margin: 0 0 4px;
      font-size: 24px;
      line-height: 1.2;
      font-weight: 700;
      letter-spacing: 0;
    }

    p {
      margin: 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.45;
    }

    button {
      appearance: none;
      border: 1px solid var(--accent);
      background: var(--accent);
      color: white;
      border-radius: 6px;
      padding: 10px 14px;
      font-size: 14px;
      font-weight: 650;
      cursor: pointer;
      white-space: nowrap;
    }

    button:hover { background: var(--accent-dark); border-color: var(--accent-dark); }

    .grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 16px;
      min-height: 520px;
    }

    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
      display: grid;
      grid-template-rows: auto 1fr;
      min-height: 520px;
    }

    .panel-title {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 12px 14px;
      border-bottom: 1px solid var(--border);
      font-size: 13px;
      font-weight: 700;
      color: #2f3a45;
    }

    .status {
      color: var(--muted);
      font-weight: 600;
      font-size: 12px;
    }

    .status.error { color: var(--danger); }

    .editor, pre {
      width: 100%;
      min-height: 100%;
      margin: 0;
      border: 0;
      padding: 16px;
      outline: none;
      font: 15px/1.5 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      color: var(--text);
      background: var(--panel);
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }

    .editor {
      overflow: auto;
    }

    .editor:empty::before {
      content: "Paste text with PII...";
      color: var(--muted);
    }

    .editor mark {
      background: #fff1a8;
      color: inherit;
      border-radius: 4px;
      padding: 1px 2px;
      cursor: help;
      box-decoration-break: clone;
      -webkit-box-decoration-break: clone;
    }

    .editor mark:hover {
      background: #ffd966;
      outline: 1px solid #d6a700;
    }

    .tooltip {
      position: fixed;
      z-index: 20;
      display: none;
      pointer-events: none;
      max-width: min(280px, calc(100vw - 24px));
      background: #17202a;
      color: #ffffff;
      border-radius: 6px;
      padding: 7px 9px;
      box-shadow: 0 8px 22px rgb(16 24 40 / 18%);
      font: 12px/1.35 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      white-space: nowrap;
    }

    .tooltip.visible {
      display: block;
    }

    pre {
      background: #fbfcfd;
      overflow: auto;
    }

    @media (max-width: 760px) {
      main { width: min(100vw - 24px, 1180px); padding: 18px 0; }
      header { align-items: stretch; flex-direction: column; }
      button { width: 100%; }
      .grid { grid-template-columns: 1fr; min-height: auto; }
      .panel { min-height: 360px; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div class="header-copy">
        <h1>PII Redactor Playground</h1>
        <p>Paste text with PII. The right side shows what would be sent to observability after redaction.</p>
        <span class="badge" id="detector-badge">Detector: loading...</span>
      </div>
      <button id="sample" type="button">Load sample</button>
    </header>

    <section class="grid" aria-label="PII redaction playground">
      <div class="panel">
        <div class="panel-title">
          <span>Input</span>
          <span class="status" id="input-count">0 chars</span>
        </div>
        <div id="input" class="editor" contenteditable="plaintext-only" spellcheck="false" role="textbox" aria-label="Input text"></div>
      </div>

      <div class="panel">
        <div class="panel-title">
          <span>Redacted</span>
          <span class="status" id="status">Ready</span>
        </div>
        <pre id="output" aria-live="polite"></pre>
      </div>
    </section>
  </main>
  <div class="tooltip" id="tooltip" role="tooltip"></div>

  <script>
    const input = document.querySelector("#input");
    const output = document.querySelector("#output");
    const statusEl = document.querySelector("#status");
    const countEl = document.querySelector("#input-count");
    const sampleButton = document.querySelector("#sample");
    const detectorBadge = document.querySelector("#detector-badge");
    const tooltip = document.querySelector("#tooltip");
    const sampleText = "Nazywam się Jan Kowalski, PESEL 85010112345, email jan.kowalski@example.com. Telefon: +48 501 222 333. Karta: 4111 1111 1111 1111.";
    let abortController = null;
    let debounceTimer = null;

    function getInputText() {
      return input.textContent || "";
    }

    function escapeHtml(value) {
      return value
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
    }

    function getCaretOffset(element) {
      const selection = window.getSelection();
      if (!selection || selection.rangeCount === 0) return element.textContent.length;
      const range = selection.getRangeAt(0);
      const prefix = range.cloneRange();
      prefix.selectNodeContents(element);
      prefix.setEnd(range.endContainer, range.endOffset);
      return prefix.toString().length;
    }

    function setCaretOffset(element, offset) {
      const selection = window.getSelection();
      if (!selection) return;
      const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
      let remaining = offset;
      let node = walker.nextNode();
      while (node) {
        if (remaining <= node.textContent.length) {
          const range = document.createRange();
          range.setStart(node, remaining);
          range.collapse(true);
          selection.removeAllRanges();
          selection.addRange(range);
          return;
        }
        remaining -= node.textContent.length;
        node = walker.nextNode();
      }
      const range = document.createRange();
      range.selectNodeContents(element);
      range.collapse(false);
      selection.removeAllRanges();
      selection.addRange(range);
    }

    function renderInput(text, spans = []) {
      const caretOffset = document.activeElement === input ? getCaretOffset(input) : null;
      let cursor = 0;
      let html = "";
      for (const span of spans) {
        html += escapeHtml(text.slice(cursor, span.start));
        const value = text.slice(span.start, span.end);
        const score = Number.isFinite(span.score) ? span.score.toFixed(3) : "n/a";
        html += `<mark tabindex="0" data-prediction="${escapeHtml(span.label)} score ${score}">${escapeHtml(value)}</mark>`;
        cursor = span.end;
      }
      html += escapeHtml(text.slice(cursor));
      input.innerHTML = html;
      if (caretOffset !== null) setCaretOffset(input, Math.min(caretOffset, text.length));
    }

    function showTooltip(mark) {
      const value = mark.dataset.prediction || "";
      if (!value) return;
      tooltip.textContent = value;
      tooltip.classList.add("visible");
      const rect = mark.getBoundingClientRect();
      const tooltipRect = tooltip.getBoundingClientRect();
      const top = Math.max(8, rect.top - tooltipRect.height - 8);
      const left = Math.min(
        window.innerWidth - tooltipRect.width - 8,
        Math.max(8, rect.left + (rect.width - tooltipRect.width) / 2)
      );
      tooltip.style.top = `${top}px`;
      tooltip.style.left = `${left}px`;
    }

    function hideTooltip() {
      tooltip.classList.remove("visible");
    }

    function setStatus(text, isError = false) {
      statusEl.textContent = text;
      statusEl.classList.toggle("error", isError);
    }

    async function loadDetectorStatus() {
      try {
        const response = await fetch("/health");
        const payload = await response.json();
        const backend = payload.detector_backend;
        detectorBadge.textContent = `Detector: ${backend}`;
        detectorBadge.classList.toggle("model", backend === "local");
      } catch {
        detectorBadge.textContent = "Detector: unknown";
      }
    }

    async function redact() {
      const text = getInputText();
      countEl.textContent = `${text.length} chars`;

      if (!text.trim()) {
        output.textContent = "";
        renderInput("");
        setStatus("Ready");
        return;
      }

      if (abortController) abortController.abort();
      abortController = new AbortController();
      setStatus("Redacting...");

      try {
        const redactRequest = fetch("/redact", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ data: text }),
          signal: abortController.signal
        });
        const detectRequest = fetch("/detect", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
          signal: abortController.signal
        });

        const [response, detectResponse] = await Promise.all([redactRequest, detectRequest]);

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        if (!detectResponse.ok) throw new Error(`HTTP ${detectResponse.status}`);
        const payload = await response.json();
        const detectPayload = await detectResponse.json();
        output.textContent = payload.data;
        renderInput(text, detectPayload.spans);
        setStatus("Done");
      } catch (error) {
        if (error.name === "AbortError") return;
        setStatus("Server error", true);
      }
    }

    input.addEventListener("input", () => {
      hideTooltip();
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(redact, 180);
    });

    input.addEventListener("mouseover", (event) => {
      const mark = event.target.closest("mark");
      if (mark && input.contains(mark)) showTooltip(mark);
    });

    input.addEventListener("mouseout", (event) => {
      if (event.target.closest("mark")) hideTooltip();
    });

    input.addEventListener("focusin", (event) => {
      const mark = event.target.closest("mark");
      if (mark && input.contains(mark)) showTooltip(mark);
    });

    input.addEventListener("focusout", hideTooltip);

    sampleButton.addEventListener("click", () => {
      renderInput(sampleText);
      redact();
      input.focus();
    });

    async function init() {
      renderInput(sampleText);
      await loadDetectorStatus();
      redact();
    }

    init();
  </script>
</body>
</html>"""


def create_app() -> FastAPI:
    detector_backend = _detector_from_env()
    threshold = float(os.getenv("PII_THRESHOLD", "0.5"))
    store_path = os.getenv("PII_STORE_PATH", "data/redacted_logs.jsonl")
    include_labels = _labels_from_env("PII_INCLUDE_LABELS")
    exclude_labels = _labels_from_env("PII_EXCLUDE_LABELS") or set()

    registry = DetectorRegistry(threshold=threshold, include_labels=include_labels, exclude_labels=exclude_labels)
    llm_provider = build_llm_provider()
    store = JsonlStore(store_path)

    app = FastAPI(title="PII Redactor Prototype")

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "detector_backend": detector_backend,
            "include_labels": sorted(include_labels) if include_labels else None,
            "exclude_labels": sorted(exclude_labels),
        }

    @app.get("/", response_class=HTMLResponse)
    @app.get("/playground", response_class=HTMLResponse)
    async def playground() -> str:
        return PLAYGROUND_HTML

    @app.post("/detect")
    async def detect(request: DetectRequest) -> dict[str, Any]:
        redactor = registry.redactor_for(detector_backend)
        return {"spans": [asdict(span) for span in redactor.spans_for_text(request.text)]}

    @app.post("/redact")
    async def redact(request: RedactRequest) -> dict[str, Any]:
        redactor = registry.redactor_for(detector_backend)
        return {"data": redactor.redact(request.data)}

    @app.post("/chat")
    async def chat(request: ChatRequest) -> dict[str, Any]:
        redactor = registry.redactor_for(detector_backend)
        raw_response = await llm_provider.complete(request.prompt)
        redacted_prompt = redactor.redact_text(request.prompt)
        redacted_response = redactor.redact_text(raw_response)
        provider_name = "demo" if isinstance(llm_provider, DemoLlmProvider) else "openrouter"
        trace = store.append(redacted_prompt, redacted_response, provider_name)
        return {
            "response": raw_response,
            "stored_trace": asdict(trace),
        }

    @app.get("/traces")
    async def traces() -> dict[str, Any]:
        return {"traces": [asdict(trace) for trace in store.list()]}

    return app


app = create_app()
