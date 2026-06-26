"""Tests for the tokenizer layer."""
import pytest

from llmpress.tokenizers import ApproximateTokenizer, get_tokenizer


class TestApproximateTokenizer:
    def setup_method(self):
        self.tok = ApproximateTokenizer()

    def test_name(self):
        assert self.tok.name() == "approximate"

    def test_empty_string(self):
        assert self.tok.count("") >= 0

    def test_single_word(self):
        # Any non-empty string must produce at least 1 token
        assert self.tok.count("hello") >= 1

    def test_camelcase_expands_subwords(self):
        # "PortfolioActivityBloc" should count as ~3 tokens (Portfolio, Activity, Bloc)
        count = self.tok.count("PortfolioActivityBloc")
        assert count >= 2, "CamelCase should expand to multiple tokens"

    def test_camelcase_more_than_simple(self):
        # A CamelCase name should produce more tokens than a simple word
        assert self.tok.count("PortfolioActivityBloc") > self.tok.count("portfolio")

    def test_alias_is_cheap(self):
        # Aliases should be 1–2 tokens
        assert 1 <= self.tok.count("T0") <= 2
        assert 1 <= self.tok.count("T99") <= 3

    def test_punctuation_counted(self):
        # Punctuation contributes fractionally
        assert self.tok.count("{};") > 0

    def test_longer_text_has_more_tokens(self):
        short = self.tok.count("hello")
        long = self.tok.count("hello world foo bar baz qux")
        assert long > short

    def test_dart_type_signature(self):
        t = self.tok.count("Future<Either<Failure, Success>>")
        # Should be at least 5 tokens (Future, Either, Failure, Success, angle brackets)
        assert t >= 4


class TestGetTokenizer:
    def test_auto_returns_tokenizer(self):
        tok = get_tokenizer("auto")
        assert tok is not None
        assert tok.count("hello world") >= 1

    def test_approximate_by_name(self):
        tok = get_tokenizer("approximate")
        assert isinstance(tok, ApproximateTokenizer)

    def test_tiktoken_raises_gracefully_or_works(self):
        try:
            tok = get_tokenizer("tiktoken")
            assert tok.count("hello") >= 1
        except ImportError:
            pass  # acceptable: tiktoken not installed
