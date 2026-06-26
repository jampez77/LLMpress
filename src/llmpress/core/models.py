from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PhraseCandidate:
    """A repeated phrase that is a candidate for compression."""

    text: str
    frequency: int
    phrase_tokens: int
    alias_tokens: int
    dict_entry_tokens: int
    net_saving: int

    @property
    def words(self) -> list[str]:
        return self.text.split()

    @property
    def word_count(self) -> int:
        return len(self.words)


@dataclass
class DictionaryEntry:
    alias: str
    original: str

    def formatted(self) -> str:
        """Single-line representation included in the compressed prompt."""
        return f"{self.alias}={self.original}"


@dataclass
class Dictionary:
    entries: list[DictionaryEntry] = field(default_factory=list)
    version: str = "1.0"

    # Alias → original lookup (built lazily).
    _lookup: dict[str, str] = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        self._lookup = {e.alias: e.original for e in self.entries}

    def lookup(self, alias: str) -> str | None:
        return self._lookup.get(alias)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "aliases": {e.alias: e.original for e in self.entries},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Dictionary:
        entries = [
            DictionaryEntry(alias=k, original=v)
            for k, v in data.get("aliases", {}).items()
        ]
        return cls(entries=entries, version=data.get("version", "1.0"))

    def is_empty(self) -> bool:
        return len(self.entries) == 0


@dataclass
class CompressionStats:
    original_chars: int
    compressed_chars: int
    dictionary_chars: int
    original_tokens: int
    compressed_tokens: int
    dictionary_tokens: int
    net_token_savings: int
    compression_ratio: float
    tokenizer_name: str
    phrases_detected: int
    phrases_compressed: int
    top_phrases: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_chars": self.original_chars,
            "compressed_chars": self.compressed_chars,
            "dictionary_chars": self.dictionary_chars,
            "original_tokens": self.original_tokens,
            "compressed_tokens": self.compressed_tokens,
            "dictionary_tokens": self.dictionary_tokens,
            "net_token_savings": self.net_token_savings,
            "compression_ratio": round(self.compression_ratio, 4),
            "tokenizer": self.tokenizer_name,
            "phrases_detected": self.phrases_detected,
            "phrases_compressed": self.phrases_compressed,
            "top_phrases": self.top_phrases,
        }


@dataclass
class CompressionResult:
    original_source: str
    compressed_source: str
    compressed_prompt: str
    dictionary: Dictionary
    stats: CompressionStats
