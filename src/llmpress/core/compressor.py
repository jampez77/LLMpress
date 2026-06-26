from __future__ import annotations

from ..core.models import CompressionResult, CompressionStats
from ..phases import (
    CommentStripper,
    DictionaryBuilder,
    Expander,
    PhraseDetector,
    Rewriter,
    WhitespaceNormalizer,
)
from ..tokenizers import Tokenizer, get_tokenizer

_PROMPT_TEMPLATE = """\
[LLMPRESS:DICT]
{dict_lines}
[END:DICT]

[LLMPRESS:RULES]
- The dictionary above maps short aliases (T0, T1, …) to their EXACT original text.
- Before analysing the source, mentally substitute every alias with its original — the source is syntactically complete once expanded.
- Do NOT flag aliases as poor variable names; they are transport-only tokens, not real identifiers.
- Do NOT invent new aliases or use Tn notation for any new code you write.
- New identifiers must follow the naming conventions visible in the source.
- When you mention an existing symbol in your response you may use its alias; it will be automatically expanded before the user sees your reply.
[END:RULES]

[LLMPRESS:TASK]
{task}
[END:TASK]

[LLMPRESS:SOURCE]
{source}
[END:SOURCE]\
"""

_PROMPT_TEMPLATE_NO_DICT = """\
[LLMPRESS:TASK]
{task}
[END:TASK]

[LLMPRESS:SOURCE]
{source}
[END:SOURCE]\
"""


class Compressor:
    """
    Orchestrate the full compression pipeline.

    Parameters
    ----------
    tokenizer:
        Token counter used for savings estimation.  Defaults to tiktoken if
        installed, otherwise the built-in heuristic.
    strip_comments:
        Remove source comments before compression (default: False — comments
        often provide context the LLM needs).
    strip_docs:
        Remove doc comments even when strip_comments=False (default: False).
    language:
        Language hint for the comment stripper ("dart", "python", "ts", …).
    min_frequency:
        A phrase must appear at least this many times to be considered.
    max_phrase_words:
        Maximum number of whitespace-separated tokens in a single alias.
    """

    def __init__(
        self,
        tokenizer: Tokenizer | None = None,
        strip_comments: bool = False,
        strip_docs: bool = False,
        language: str = "auto",
        min_frequency: int = 2,
        max_phrase_words: int = 6,
    ) -> None:
        self._tok = tokenizer or get_tokenizer("auto")
        self._strip_comments = strip_comments
        self._strip_docs = strip_docs
        self._language = language
        self._whitespace = WhitespaceNormalizer()
        self._detector = PhraseDetector(
            tokenizer=self._tok,
            min_frequency=min_frequency,
            max_phrase_words=max_phrase_words,
        )
        self._builder = DictionaryBuilder(min_frequency=min_frequency)
        self._rewriter = Rewriter()

    def compress(self, source: str, prompt: str) -> CompressionResult:
        # --- Phase 1: normalise whitespace ---
        normalised = self._whitespace.apply(source)

        # --- Phase 2: optional comment stripping ---
        if self._strip_comments or self._strip_docs:
            stripper = CommentStripper(language=self._language, strip_docs=self._strip_docs)
            normalised = stripper.apply(normalised)

        # --- Phase 3: phrase detection ---
        candidates = self._detector.detect(normalised)

        # --- Phase 4: build dictionary (pass source for overlap elimination) ---
        dictionary = self._builder.build(candidates, source=normalised)

        # --- Phase 5: rewrite source ---
        compressed_source = self._rewriter.rewrite(normalised, dictionary)

        # --- Phase 6: build final prompt ---
        if dictionary.is_empty():
            compressed_prompt = _PROMPT_TEMPLATE_NO_DICT.format(
                task=prompt.strip(),
                source=compressed_source,
            )
        else:
            dict_lines = "\n".join(e.formatted() for e in dictionary.entries)
            compressed_prompt = _PROMPT_TEMPLATE.format(
                dict_lines=dict_lines,
                task=prompt.strip(),
                source=compressed_source,
            )

        # --- Phase 7: compute stats ---
        stats = self._build_stats(
            original_source=normalised,
            compressed_source=compressed_source,
            prompt=prompt,
            compressed_prompt=compressed_prompt,
            dictionary=dictionary,
            candidates=candidates,
            n_compressed=len(dictionary.entries),
        )

        return CompressionResult(
            original_source=normalised,
            compressed_source=compressed_source,
            compressed_prompt=compressed_prompt,
            dictionary=dictionary,
            stats=stats,
        )

    def _build_stats(
        self,
        original_source: str,
        compressed_source: str,
        prompt: str,
        compressed_prompt: str,
        dictionary,
        candidates: list,
        n_compressed: int,
    ) -> CompressionStats:
        # Fair comparison: original = prompt + source (what the user would send).
        # Compressed = prompt + compressed_source + dict overhead.
        # Template markers (LLMPRESS:DICT etc.) are a small fixed overhead.
        original_content = f"{prompt}\n{original_source}"
        dict_lines = "\n".join(e.formatted() for e in dictionary.entries)

        orig_tokens = self._tok.count(original_content)
        src_tokens = self._tok.count(compressed_source)
        prompt_tokens = self._tok.count(prompt)
        dict_tokens = self._tok.count(dict_lines) if dict_lines else 0

        # Total compressed = prompt + compressed_source + dictionary overhead
        comp_tokens = prompt_tokens + src_tokens + dict_tokens
        net_saving = max(0, orig_tokens - comp_tokens)

        top_phrases = [
            {
                "phrase": c.text[:80],
                "frequency": c.frequency,
                "phrase_tokens": c.phrase_tokens,
                "net_saving": c.net_saving,
            }
            for c in candidates[:10]
        ]

        return CompressionStats(
            original_chars=len(original_content),
            compressed_chars=len(compressed_source),
            dictionary_chars=len(dict_lines),
            original_tokens=orig_tokens,
            compressed_tokens=comp_tokens,
            dictionary_tokens=dict_tokens,
            net_token_savings=net_saving,
            compression_ratio=comp_tokens / orig_tokens if orig_tokens > 0 else 1.0,
            tokenizer_name=self._tok.name(),
            phrases_detected=len(candidates),
            phrases_compressed=n_compressed,
            top_phrases=top_phrases,
        )
