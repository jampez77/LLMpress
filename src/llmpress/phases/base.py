from abc import ABC, abstractmethod


class Phase(ABC):
    """Single transformation step in the compression pipeline."""

    @abstractmethod
    def apply(self, source: str) -> str:
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__
