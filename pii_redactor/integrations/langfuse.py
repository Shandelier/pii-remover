from __future__ import annotations

from typing import Any, Callable

from pii_redactor.core.detectors import build_detector
from pii_redactor.core.redactor import Redactor


def make_mask(backend: str = "regex", threshold: float = 0.5) -> Callable[[Any], Any]:
    redactor = Redactor(detector=build_detector(backend=backend, threshold=threshold))

    def mask(data: Any, **_: Any) -> Any:
        return redactor.redact(data)

    return mask
