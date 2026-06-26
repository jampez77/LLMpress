"""Tests for phrase detection and savings scoring."""
import pytest

from llmpress.core.models import PhraseCandidate
from llmpress.phases.phrase_detector import PhraseDetector
from llmpress.tokenizers import ApproximateTokenizer


@pytest.fixture()
def detector():
    return PhraseDetector(tokenizer=ApproximateTokenizer(), min_frequency=2)


def test_detects_repeated_identifier(detector):
    source = "PortfolioActivityBloc extends PortfolioActivityBloc creates PortfolioActivityBloc"
    candidates = detector.detect(source)
    texts = [c.text for c in candidates]
    assert "PortfolioActivityBloc" in texts


def test_single_occurrence_not_detected(detector):
    source = "PortfolioActivityBloc extends Bloc"
    candidates = detector.detect(source)
    texts = [c.text for c in candidates]
    assert "PortfolioActivityBloc" not in texts


def test_short_words_skipped(detector):
    # "void", "if", "is" etc. should not produce profitable aliases
    source = "void foo() { void bar() { void baz() { void qux() { if (x is void) {} } } } }"
    candidates = detector.detect(source)
    short_texts = [c.text for c in candidates if len(c.text) < 5]
    assert short_texts == []


def test_profitable_multiword_phrase(detector):
    # "result.fold" appearing 3 times with a longer context should be detected
    phrase = "result.fold( (failure) => emit(Error"
    source = (phrase + " X) ") * 4
    candidates = detector.detect(source)
    assert len(candidates) > 0


def test_sorted_by_savings(detector):
    source = (
        "PortfolioActivityBloc " * 5
        + "BlocBuilder " * 3
        + "Bloc " * 2
    )
    candidates = detector.detect(source)
    if len(candidates) >= 2:
        for a, b in zip(candidates, candidates[1:]):
            assert a.net_saving >= b.net_saving


def test_net_saving_positive(detector):
    source = "PortfolioActivityBloc extends PortfolioActivityBloc PortfolioActivityBloc PortfolioActivityBloc"
    candidates = detector.detect(source)
    for c in candidates:
        assert c.net_saving > 0, f"Non-positive saving: {c}"


def test_candidates_have_correct_fields(detector):
    source = "UserRepository fetch UserRepository update UserRepository delete UserRepository"
    candidates = detector.detect(source)
    for c in candidates:
        assert isinstance(c, PhraseCandidate)
        assert c.frequency >= 2
        assert c.phrase_tokens > 0
        assert c.alias_tokens > 0
        assert c.dict_entry_tokens > 0


def test_min_frequency_respected():
    det = PhraseDetector(tokenizer=ApproximateTokenizer(), min_frequency=3)
    # Appears only 2 times — should NOT be detected with min_frequency=3
    source = "PortfolioActivityBloc one PortfolioActivityBloc two"
    candidates = det.detect(source)
    texts = [c.text for c in candidates]
    assert "PortfolioActivityBloc" not in texts


def test_phrase_too_long_skipped(detector):
    # An extremely long phrase should be skipped even if repeated
    very_long = "alpha bravo charlie delta echo foxtrot golf hotel india julep"
    source = (very_long + " X ") * 4
    candidates = detector.detect(source)
    # No single alias should cover the entire long phrase
    for c in candidates:
        assert len(c.words) <= 8


def test_dart_bloc_pattern():
    det = PhraseDetector(tokenizer=ApproximateTokenizer(), min_frequency=2)
    dart = """\
class UserBloc extends Bloc<UserEvent, UserState> {
  final UserRepository _userRepository;
  UserBloc({required UserRepository userRepository})
      : _userRepository = userRepository, super(UserInitial()) {
    on<LoadUser>(_onLoadUser);
    on<UpdateUser>(_onUpdateUser);
  }
  Future<void> _onLoadUser(LoadUser event, Emitter<UserState> emit) async {
    emit(UserLoading());
    final result = await _userRepository.getUser(event.id);
    result.fold(
      (failure) => emit(UserError(failure: failure)),
      (user) => emit(UserLoaded(user: user)),
    );
  }
  Future<void> _onUpdateUser(UpdateUser event, Emitter<UserState> emit) async {
    emit(UserLoading());
    final result = await _userRepository.updateUser(event.user);
    result.fold(
      (failure) => emit(UserError(failure: failure)),
      (user) => emit(UserLoaded(user: user)),
    );
  }
}"""
    candidates = det.detect(dart)
    assert len(candidates) > 0
    # Should find UserRepository, UserState, or emit(UserLoading()) pattern
    combined = " ".join(c.text for c in candidates)
    assert any(kw in combined for kw in ["User", "emit", "result"])
