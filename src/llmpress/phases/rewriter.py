from __future__ import annotations

import re

from ..core.models import Dictionary, DictionaryEntry

# Identifiers contain only word chars — a plain word-boundary match is safe.
_IDENT_RE = re.compile(r"^\w+$")


def _is_identifier(text: str) -> bool:
    return bool(_IDENT_RE.match(text))


def _replace_identifier(source: str, original: str, alias: str) -> str:
    """Word-boundary replacement so 'Bloc' inside 'BlocProvider' is not touched."""
    return re.sub(r"\b" + re.escape(original) + r"\b", alias, source)


def _replace_phrase(source: str, original: str, alias: str) -> str:
    """Plain string replacement for multi-word / punctuation-containing phrases."""
    return source.replace(original, alias)


class Rewriter:
    """
    Apply a Dictionary to source, replacing each original phrase with its alias.

    Ordering: longest original text first so that
    ``Future<Either<Failure, T>>`` is replaced before any sub-phrase
    like ``Either<Failure`` if both happen to be in the dictionary.
    """

    def rewrite(self, source: str, dictionary: Dictionary) -> str:
        if dictionary.is_empty():
            return source

        ordered = sorted(
            dictionary.entries, key=lambda e: len(e.original), reverse=True
        )
        result = source
        for entry in ordered:
            if _is_identifier(entry.original):
                result = _replace_identifier(result, entry.original, entry.alias)
            else:
                result = _replace_phrase(result, entry.original, entry.alias)
        return result


class Expander:
    """
    Reverse a Rewriter: replace every alias with its original text.

    Processes aliases longest-first (``T10`` before ``T1``) to avoid
    partial expansions.
    """

    def expand(self, text: str, dictionary: Dictionary) -> str:
        if dictionary.is_empty():
            return text

        ordered = sorted(
            dictionary.entries, key=lambda e: len(e.alias), reverse=True
        )
        result = text
        for entry in ordered:
            original = entry.original
            result = re.sub(
                r"\b" + re.escape(entry.alias) + r"\b",
                lambda _m, o=original: o,
                result,
            )
        return result
