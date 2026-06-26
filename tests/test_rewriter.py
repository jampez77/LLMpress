"""Tests for Rewriter and Expander."""
import pytest

from llmpress.core.models import Dictionary, DictionaryEntry
from llmpress.phases.rewriter import Expander, Rewriter


def make_dict(*pairs: tuple) -> Dictionary:
    entries = [DictionaryEntry(alias=a, original=o) for a, o in pairs]
    return Dictionary(entries=entries)


@pytest.fixture()
def rewriter():
    return Rewriter()


@pytest.fixture()
def expander():
    return Expander()


# ── Rewriter ──────────────────────────────────────────────────────────────

class TestRewriter:
    def test_empty_dictionary(self, rewriter):
        source = "class Foo extends Bar {}"
        d = make_dict()
        assert rewriter.rewrite(source, d) == source

    def test_single_identifier(self, rewriter):
        d = make_dict(("T0", "PortfolioActivityBloc"))
        source = "class PortfolioActivityBloc extends Bloc {}"
        result = rewriter.rewrite(source, d)
        assert "T0" in result
        assert "PortfolioActivityBloc" not in result

    def test_identifier_word_boundary(self, rewriter):
        # "Bloc" should not replace the "Bloc" inside "BlocProvider"
        d = make_dict(("T0", "Bloc"))
        source = "class BlocProvider extends Bloc {}"
        result = rewriter.rewrite(source, d)
        assert "BlocProvider" in result  # untouched
        assert "T0Provider" not in result

    def test_multiword_phrase(self, rewriter):
        d = make_dict(("T0", "result.fold( (failure) =>"))
        source = "result.fold( (failure) => emit(Error));"
        result = rewriter.rewrite(source, d)
        assert "T0" in result

    def test_longer_phrase_replaced_first(self, rewriter):
        # Longer phrases must be replaced before shorter sub-phrases
        d = make_dict(
            ("T0", "PortfolioActivityBloc"),
            ("T1", "Portfolio"),
        )
        source = "PortfolioActivityBloc extends Portfolio"
        result = rewriter.rewrite(source, d)
        assert "T0" in result
        # Portfolio should only appear where it was standalone
        assert "T0Activity" not in result

    def test_all_occurrences_replaced(self, rewriter):
        d = make_dict(("T0", "UserRepository"))
        source = "UserRepository a = UserRepository(); x.UserRepository()"
        result = rewriter.rewrite(source, d)
        assert "UserRepository" not in result


# ── Expander ──────────────────────────────────────────────────────────────

class TestExpander:
    def test_empty_dictionary(self, expander):
        text = "T0 extends T1 {}"
        d = make_dict()
        assert expander.expand(text, d) == text

    def test_single_alias(self, expander):
        d = make_dict(("T0", "PortfolioActivityBloc"))
        text = "The T0 class handles portfolio events."
        result = expander.expand(text, d)
        assert "PortfolioActivityBloc" in result
        assert "T0" not in result

    def test_multiple_aliases(self, expander):
        d = make_dict(
            ("T0", "PortfolioActivityBloc"),
            ("T1", "PortfolioRepository"),
        )
        text = "class T0 { T1 repo; }"
        result = expander.expand(text, d)
        assert "PortfolioActivityBloc" in result
        assert "PortfolioRepository" in result

    def test_longer_alias_expanded_first(self, expander):
        # T10 must not be treated as T1 + "0"
        d = make_dict(
            ("T1", "Alpha"),
            ("T10", "Beta"),
        )
        text = "T10 and T1 appear here"
        result = expander.expand(text, d)
        assert "Beta" in result
        assert "Alpha" in result
        assert "Alpha0" not in result

    def test_new_identifiers_preserved(self, expander):
        # LLM-introduced human-readable names must pass through unchanged
        d = make_dict(("T0", "UserRepository"))
        text = "T0 and the new PortfolioCache should be used."
        result = expander.expand(text, d)
        assert "PortfolioCache" in result

    def test_roundtrip_identity(self, rewriter, expander):
        # rewrite then expand should produce the original source
        d = make_dict(
            ("T0", "PortfolioActivityBloc"),
            ("T1", "UserRepository"),
        )
        source = "class PortfolioActivityBloc { UserRepository repo; PortfolioActivityBloc(UserRepository r); }"
        compressed = rewriter.rewrite(source, d)
        restored = expander.expand(compressed, d)
        assert restored == source
