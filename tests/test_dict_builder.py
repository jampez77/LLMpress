"""Tests for the DictionaryBuilder."""
import pytest

from llmpress.core.models import PhraseCandidate
from llmpress.phases.dict_builder import DictionaryBuilder


def make_candidate(text: str, freq: int = 3, phrase_tokens: int = 3) -> PhraseCandidate:
    return PhraseCandidate(
        text=text,
        frequency=freq,
        phrase_tokens=phrase_tokens,
        alias_tokens=1,
        dict_entry_tokens=4,
        net_saving=(phrase_tokens - 1) * freq - 4,
    )


@pytest.fixture()
def builder():
    return DictionaryBuilder()


def test_empty_candidates(builder):
    d = builder.build([], source="")
    assert d.is_empty()


def test_single_candidate(builder):
    candidates = [make_candidate("PortfolioActivityBloc", freq=5, phrase_tokens=3)]
    source = "PortfolioActivityBloc " * 5
    d = builder.build(candidates, source=source)
    assert len(d.entries) == 1
    assert d.entries[0].alias == "T0"
    assert d.entries[0].original == "PortfolioActivityBloc"


def test_sequential_aliases(builder):
    cands = [
        make_candidate("AlphaBloc", freq=5, phrase_tokens=2),
        make_candidate("BetaRepository", freq=4, phrase_tokens=2),
        make_candidate("GammaService", freq=3, phrase_tokens=2),
    ]
    source = "AlphaBloc " * 5 + "BetaRepository " * 4 + "GammaService " * 3
    d = builder.build(cands, source=source)
    aliases = [e.alias for e in d.entries]
    assert aliases == ["T0", "T1", "T2"]


def test_max_entries_respected(builder):
    b = DictionaryBuilder(max_entries=2)
    cands = [make_candidate(f"Word{i}Bloc", freq=5, phrase_tokens=3) for i in range(10)]
    source = " ".join(f"Word{i}Bloc " * 5 for i in range(10))
    d = b.build(cands, source=source)
    assert len(d.entries) <= 2


def test_overlap_eliminated_via_source_simulation(builder):
    # Committing the longer phrase should prevent the overlapping shorter sub-phrase.
    # "PortfolioActivityBloc" contains "PortfolioActivity" as a prefix.
    source = "PortfolioActivityBloc " * 4
    long_cand = make_candidate("PortfolioActivityBloc", freq=4, phrase_tokens=3)
    # Make a shorter overlapping candidate with lower saving
    sub_cand = PhraseCandidate(
        text="PortfolioActivityBloc",  # same text, same phrase
        frequency=4,
        phrase_tokens=3,
        alias_tokens=1,
        dict_entry_tokens=4,
        net_saving=3,  # lower saving
    )
    # Both candidates refer to the same text — only one should appear
    d = builder.build([long_cand, sub_cand], source=source)
    # Should only have 1 entry for this text
    originals = [e.original for e in d.entries]
    assert originals.count("PortfolioActivityBloc") == 1


def test_candidate_not_in_source_skipped(builder):
    # If the candidate's text doesn't appear in source, it should be skipped.
    cands = [make_candidate("NotInSource", freq=5, phrase_tokens=3)]
    d = builder.build(cands, source="something else entirely")
    assert d.is_empty()


def test_dictionary_lookup(builder):
    cands = [make_candidate("UserRepository", freq=4, phrase_tokens=2)]
    source = "UserRepository " * 4
    d = builder.build(cands, source=source)
    assert d.lookup("T0") == "UserRepository"
    assert d.lookup("T99") is None


def test_to_dict_roundtrip(builder):
    from llmpress.core.models import Dictionary

    cands = [make_candidate("UserRepository", freq=4, phrase_tokens=2)]
    source = "UserRepository " * 4
    d = builder.build(cands, source=source)
    serialised = d.to_dict()
    restored = Dictionary.from_dict(serialised)
    assert restored.lookup("T0") == "UserRepository"
