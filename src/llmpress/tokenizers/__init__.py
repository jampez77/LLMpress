from .approximate import ApproximateTokenizer
from .base import Tokenizer
from .tiktoken_adapter import TiktokenTokenizer

__all__ = ["Tokenizer", "ApproximateTokenizer", "TiktokenTokenizer"]


def get_tokenizer(name: str = "auto") -> Tokenizer:
    """
    Resolve a tokenizer by name.

    "auto"        — tiktoken if available, else approximate
    "approximate" — always use the heuristic tokenizer
    "tiktoken"    — tiktoken with gpt-4o (raises if not installed)
    "tiktoken:X"  — tiktoken with model X
    """
    if name == "approximate":
        return ApproximateTokenizer()
    if name.startswith("tiktoken"):
        model = name.split(":", 1)[1] if ":" in name else "gpt-4o"
        return TiktokenTokenizer(model=model)
    # auto
    try:
        return TiktokenTokenizer()
    except ImportError:
        return ApproximateTokenizer()
