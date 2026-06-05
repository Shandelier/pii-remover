import pytest

from pii_redactor.core.detectors import BardsAiOnnxDetector, build_detector


class FakeEncoding:
    def __init__(self, name: str, overflowing: list["FakeEncoding"] | None = None) -> None:
        self.name = name
        self.overflowing = overflowing or []


class FakeTokenizer:
    def __init__(self, encoding: FakeEncoding) -> None:
        self.encoding = encoding

    def encode(self, text: str) -> FakeEncoding:
        assert text == "long text"
        return self.encoding


def test_bards_detector_uses_tokenizer_overflow_chunks(monkeypatch) -> None:
    overflow = FakeEncoding("overflow")
    first = FakeEncoding("first", overflowing=[overflow])
    detector = object.__new__(BardsAiOnnxDetector)
    detector._tokenizer = FakeTokenizer(first)

    assert detector._chunked_encodings("long text") == [first, overflow]


def test_regex_backend_is_not_supported() -> None:
    with pytest.raises(ValueError, match="Unsupported detector backend: regex"):
        build_detector("regex")
