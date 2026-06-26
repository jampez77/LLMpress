from __future__ import annotations

import re

from ..core.models import Dictionary, DictionaryEntry, PhraseCandidate
from .rewriter import _is_identifier, _replace_identifier, _replace_phrase


class DictionaryBuilder:
    """
    Greedily select the most profitable non-overlapping phrases and assign
    sequential aliases (T0, T1, T2, …).

    Overlap elimination
    -------------------
    After each phrase is committed, it is immediately applied to a working copy
    of the source.  The next candidate is only accepted if it still appears in
    the *modified* source at least ``min_frequency`` times.  This naturally
    handles all overlap types — containment, partial, and n-gram interleaving —
    without explicit text comparison.

    The greedy ordering (highest net_saving first) maximises first-order savings
    without back-tracking.
    """

    def __init__(
        self,
        alias_prefix: str = "T",
        max_entries: int = 100,
        min_frequency: int = 2,
    ) -> None:
        self._prefix = alias_prefix
        self._max_entries = max_entries
        self._min_freq = min_frequency

    def build(
        self,
        candidates: list[PhraseCandidate],
        source: str = "",
    ) -> Dictionary:
        """
        *candidates* must already be sorted descending by net_saving.

        *source* is the normalised source text.  When provided, overlap
        elimination is done by simulating replacements on a working copy.
        """
        working = source
        entries: list[DictionaryEntry] = []

        for candidate in candidates:
            if len(entries) >= self._max_entries:
                break

            alias = f"{self._prefix}{len(entries)}"
            text = candidate.text

            # Verify the phrase still appears enough times in the working source.
            actual_freq = self._count_occurrences(text, working)
            if actual_freq < self._min_freq:
                continue

            entries.append(DictionaryEntry(alias=alias, original=text))

            # Apply the replacement to the working copy so subsequent
            # candidates see the already-compressed source.
            if working:
                if _is_identifier(text):
                    working = _replace_identifier(working, text, alias)
                else:
                    working = _replace_phrase(working, text, alias)

        return Dictionary(entries=entries)

    @staticmethod
    def _count_occurrences(text: str, source: str) -> int:
        if not source:
            return 0
        if _is_identifier(text):
            return len(re.findall(r"\b" + re.escape(text) + r"\b", source))
        return source.count(text)
