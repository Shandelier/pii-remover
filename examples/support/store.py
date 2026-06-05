from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class StoredTrace:
    id: str
    created_at: str
    redacted_prompt: str
    redacted_response: str
    provider: str


class JsonlStore:
    def __init__(self, path: Path | str = "data/redacted_logs.jsonl") -> None:
        self.path = Path(path)

    def append(self, redacted_prompt: str, redacted_response: str, provider: str) -> StoredTrace:
        trace = StoredTrace(
            id=str(uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            redacted_prompt=redacted_prompt,
            redacted_response=redacted_response,
            provider=provider,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(asdict(trace), ensure_ascii=False) + "\n")
        return trace

    def list(self) -> list[StoredTrace]:
        if not self.path.exists():
            return []
        traces = []
        with self.path.open(encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    traces.append(StoredTrace(**json.loads(line)))
        return traces
