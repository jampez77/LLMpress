"""Tests for compression statistics."""
import pytest

from llmpress import Compressor
from llmpress.tokenizers import ApproximateTokenizer


@pytest.fixture()
def comp():
    return Compressor(tokenizer=ApproximateTokenizer())


def test_stats_to_dict_has_all_fields(comp):
    result = comp.compress("void foo() {}", "Review.")
    d = result.stats.to_dict()
    required = [
        "original_tokens", "compressed_tokens", "dictionary_tokens",
        "net_token_savings", "compression_ratio", "tokenizer",
        "phrases_detected", "phrases_compressed", "top_phrases",
    ]
    for key in required:
        assert key in d, f"Missing key: {key}"


def test_stats_original_tokens_counts_prompt_and_source(comp):
    prompt = "Review this carefully."
    source = "class Foo { void bar() {} }"
    result = comp.compress(source, prompt)
    # Original tokens must include both prompt and source
    tok = ApproximateTokenizer()
    expected_min = tok.count(prompt) + tok.count(source) - 5  # some tolerance
    assert result.stats.original_tokens >= expected_min


def test_stats_net_savings_non_negative(comp):
    source = "UserBloc extends UserRepository UserBloc " * 5
    result = comp.compress(source, "Review.")
    assert result.stats.net_token_savings >= 0


def test_stats_compression_ratio_type(comp):
    result = comp.compress("int x = 1;", "Review.")
    assert isinstance(result.stats.compression_ratio, float)


def test_stats_top_phrases_list(comp):
    source = "PortfolioActivityBloc " * 5 + "UserRepository " * 4
    result = comp.compress(source, "Review.")
    assert isinstance(result.stats.top_phrases, list)


def test_stats_phrases_detected_matches_candidates(comp):
    source = """\
class UserBloc extends Bloc<UserEvent, UserState> {
  final UserRepository _repo;
  UserBloc(UserRepository repo) : _repo = repo, super(UserInitial());
  void _onLoad(LoadUser event, Emitter<UserState> emit) async {
    emit(UserLoading());
    final r = await _repo.getUser(event.id);
    r.fold((f) => emit(UserError(f)), (u) => emit(UserLoaded(u)));
  }
  void _onUpdate(UpdateUser event, Emitter<UserState> emit) async {
    emit(UserLoading());
    final r = await _repo.updateUser(event.user);
    r.fold((f) => emit(UserError(f)), (u) => emit(UserLoaded(u)));
  }
}"""
    result = comp.compress(source, "Review.")
    assert result.stats.phrases_detected >= result.stats.phrases_compressed


def test_stats_tokenizer_name_in_output(comp):
    result = comp.compress("void foo() {}", "Review.")
    assert result.stats.to_dict()["tokenizer"] == "approximate"
