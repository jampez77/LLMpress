import re

from .base import Tokenizer

# Split on CamelCase transitions:  "PortfolioBloc" → "Portfolio Bloc"
_CAMEL_SPLIT = re.compile(
    r"(?<=[a-z0-9])(?=[A-Z])"         # lowerUpper
    r"|(?<=[A-Z]{2})(?=[A-Z][a-z])"   # ABCDef → ABC Def
)


def _expand_subwords(text: str) -> str:
    """Expand CamelCase so each subword counts as one token."""
    return _CAMEL_SPLIT.sub(" ", text)


class ApproximateTokenizer(Tokenizer):
    """
    Heuristic tokenizer that approximates GPT-4 BPE without a hard dependency.

    Key insight: CamelCase identifiers like ``PortfolioActivityBloc`` are split
    by the BPE tokenizer into subwords (Portfolio + Activity + Bloc = 3 tokens).
    We replicate this by expanding CamelCase before counting words.

    Accuracy: ±20% on typical source files; good enough for compression
    savings estimation.  Swap for TiktokenTokenizer for exact counts.
    """

    def count(self, text: str) -> int:
        expanded = _expand_subwords(text)
        words = len(re.findall(r"\w+", expanded))
        punct = len(re.findall(r"[^\w\s]", text))
        return max(1, words + int(punct * 0.3))

    def name(self) -> str:
        return "approximate"
