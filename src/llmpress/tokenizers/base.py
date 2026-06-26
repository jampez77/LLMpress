from abc import ABC, abstractmethod


class Tokenizer(ABC):
    """Abstract token counter — pluggable so any LLM tokenizer can be wired in."""

    @abstractmethod
    def count(self, text: str) -> int:
        """Return the number of LLM tokens in *text*."""
        ...

    @abstractmethod
    def name(self) -> str:
        """Human-readable name used in stats output."""
        ...
