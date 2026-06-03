from __future__ import annotations

import os
from typing import Any, Callable

from pii_redactor.core.detectors import build_detector
from pii_redactor.core.redactor import Redactor


def make_mask(backend: str | None = None, threshold: float | None = None) -> Callable[[Any], Any]:
    """Return a Langfuse-compatible mask(data, **kwargs) function."""

    resolved_backend = backend or os.getenv("PII_DETECTOR_BACKEND", "regex")
    resolved_threshold = threshold if threshold is not None else float(os.getenv("PII_THRESHOLD", "0.5"))
    redactor = Redactor(detector=build_detector(backend=resolved_backend, threshold=resolved_threshold))

    def mask(data: Any, **_: Any) -> Any:
        return redactor.redact(data)

    return mask
