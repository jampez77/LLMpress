from .base import Tokenizer


class TiktokenTokenizer(Tokenizer):
    """Exact token counter using tiktoken (requires `pip install tiktoken`)."""

    def __init__(self, model: str = "gpt-4o") -> None:
        try:
            import tiktoken  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "tiktoken is not installed. Run: pip install llmpress[tiktoken]"
            ) from exc
        self._enc = tiktoken.encoding_for_model(model)
        self._model = model

    def count(self, text: str) -> int:
        return len(self._enc.encode(text))

    def name(self) -> str:
        return f"tiktoken:{self._model}"
