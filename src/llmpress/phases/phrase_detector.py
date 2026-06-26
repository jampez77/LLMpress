from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from ..core.models import PhraseCandidate
from ..tokenizers.base import Tokenizer

# Identifier: starts with letter/underscore, minimum 5 chars.
_IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{4,}\b")

# Whitespace-separated word splitter for n-gram detection.
_WORD_RE = re.compile(r"\S+")

# Phrases longer than this (in LLM tokens) are skipped.
_MAX_PHRASE_TOKENS = 10

# Minimum chars in a phrase.
_MIN_PHRASE_CHARS = 5

# Keywords that must NOT start a multi-word alias phrase.
# Replacing "extends Foo" with T0 produces "class Bar T0 {" which looks like
# a syntax error and strips all structural context from the code.
_STRUCTURAL_PREFIXES = frozenset({
    # inheritance / composition
    "extends", "implements", "with", "mixin",
    # declaration modifiers
    "abstract", "class", "interface", "enum", "typedef", "type",
    "final", "const", "late", "static", "override", "required",
    "public", "private", "protected", "internal", "sealed",
    "readonly", "virtual", "async", "await", "yield",
    # control flow (multi-word patterns starting here are structural)
    "if", "else", "for", "while", "do", "switch", "case", "return",
    "throw", "try", "catch", "finally",
    # common type keywords that produce short, marginal aliases
    "void", "bool", "int", "double", "float", "string", "String",
    "List", "Map", "Set", "Future", "Stream",
})


@dataclass
class _RawCandidate:
    text: str
    frequency: int
    is_identifier: bool


class PhraseDetector:
    """
    Detect repeated token sequences in *normalised* source code and score them
    for compression profit.

    Two-pass strategy
    -----------------
    **Pass 1 – Identifier scan**
        Use ``\\b`` word-boundary regex to find every long identifier (≥ 5 chars)
        that appears more than once.  CamelCase names like
        ``PortfolioActivityBloc`` score well because BPE tokenisers split them
        into subwords (Portfolio + Activity + Bloc = 3 tokens).

    **Pass 2 – Whitespace n-gram scan**
        Treat the source as a sequence of whitespace-separated tokens and find
        repeated 2–N token sequences.

    Scoring
    -------
    ::

        net_saving = (phrase_tokens − alias_tokens) × frequency − dict_entry_tokens

    Only candidates with ``net_saving > 0`` are returned, sorted descending.
    Phrases exceeding ``max_phrase_tokens`` LLM tokens are dropped — their
    dictionary entries cost more than they save.
    """

    def __init__(
        self,
        tokenizer: Tokenizer,
        min_frequency: int = 2,
        max_phrase_words: int = 6,
        alias_prefix: str = "T",
    ) -> None:
        self._tok = tokenizer
        self._min_freq = min_frequency
        self._max_phrase_words = max_phrase_words
        self._prefix = alias_prefix
        self._alias_tokens = self._tok.count(f"{alias_prefix}0")

    def detect(self, source: str) -> list[PhraseCandidate]:
        raw: list[_RawCandidate] = []
        raw.extend(self._scan_identifiers(source))
        raw.extend(self._scan_ngrams(source))

        # Deduplicate by text
        seen: set[str] = set()
        deduped: list[_RawCandidate] = []
        for r in raw:
            if r.text not in seen:
                seen.add(r.text)
                deduped.append(r)

        candidates: list[PhraseCandidate] = []
        for r in deduped:
            c = self._score(r)
            if c is not None:
                candidates.append(c)

        candidates.sort(key=lambda c: c.net_saving, reverse=True)
        return candidates

    # ------------------------------------------------------------------

    def _scan_identifiers(self, source: str) -> list[_RawCandidate]:
        counts: Counter[str] = Counter(_IDENT_RE.findall(source))
        return [
            _RawCandidate(text=text, frequency=freq, is_identifier=True)
            for text, freq in counts.items()
            if freq >= self._min_freq
            and len(text) >= _MIN_PHRASE_CHARS
            and text not in _STRUCTURAL_PREFIXES
        ]

    def _scan_ngrams(self, source: str) -> list[_RawCandidate]:
        words = _WORD_RE.findall(source)
        n = len(words)
        counts: Counter[tuple[str, ...]] = Counter()
        for length in range(2, min(self._max_phrase_words + 1, n + 1)):
            for i in range(n - length + 1):
                counts[tuple(words[i : i + length])] += 1

        result: list[_RawCandidate] = []
        for ngram, freq in counts.items():
            if freq < self._min_freq:
                continue
            # Skip phrases that start with a structural keyword — replacing
            # "extends Foo" with T0 produces "class Bar T0 {" which looks like
            # a syntax error and strips semantic context from the code.
            if ngram[0] in _STRUCTURAL_PREFIXES:
                continue
            text = " ".join(ngram)
            if len(text) < _MIN_PHRASE_CHARS:
                continue
            # Reject overly long phrases before calling the tokenizer.
            if self._tok.count(text) > _MAX_PHRASE_TOKENS:
                continue
            result.append(_RawCandidate(text=text, frequency=freq, is_identifier=False))
        return result

    def _score(self, raw: _RawCandidate) -> PhraseCandidate | None:
        phrase_tokens = self._tok.count(raw.text)
        if phrase_tokens <= self._alias_tokens:
            return None
        if phrase_tokens > _MAX_PHRASE_TOKENS:
            return None

        dict_entry_tokens = self._tok.count(
            f"{self._prefix}0={raw.text}\n"
        )
        net_saving = (
            (phrase_tokens - self._alias_tokens) * raw.frequency
            - dict_entry_tokens
        )
        if net_saving <= 0:
            return None

        return PhraseCandidate(
            text=raw.text,
            frequency=raw.frequency,
            phrase_tokens=phrase_tokens,
            alias_tokens=self._alias_tokens,
            dict_entry_tokens=dict_entry_tokens,
            net_saving=net_saving,
        )
