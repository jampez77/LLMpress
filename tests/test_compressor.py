"""Tests for the end-to-end Compressor."""
import pytest

from llmpress import Compressor
from llmpress.tokenizers import ApproximateTokenizer


@pytest.fixture()
def comp():
    return Compressor(tokenizer=ApproximateTokenizer())


class TestCompressorBasics:
    def test_returns_result(self, comp):
        result = comp.compress("void foo() {}", "Review.")
        assert result is not None
        assert result.compressed_prompt
        assert result.dictionary is not None
        assert result.stats is not None

    def test_compressed_prompt_has_task_section(self, comp):
        result = comp.compress("class Foo {}", "Find bugs.")
        assert "Find bugs." in result.compressed_prompt

    def test_compressed_prompt_has_source(self, comp):
        result = comp.compress("class Foo { void foo() {} }", "Review.")
        # The source (possibly with aliases) must be in the prompt
        assert "[LLMPRESS:SOURCE]" in result.compressed_prompt

    def test_stats_original_tokens_positive(self, comp):
        result = comp.compress("class UserBloc extends Bloc {}", "Review.")
        assert result.stats.original_tokens > 0

    def test_stats_compression_ratio_valid(self, comp):
        result = comp.compress("void x() {}", "Review.")
        assert 0.0 < result.stats.compression_ratio <= 2.0

    def test_small_file_may_not_compress(self, comp):
        # A tiny file with no repetition should just pass through cleanly
        result = comp.compress("int x = 1;", "Review.")
        # No crash; ratio can be >= 1 (template overhead)
        assert result.stats is not None

    def test_strip_comments_removes_comments(self):
        c = Compressor(tokenizer=ApproximateTokenizer(), strip_comments=True, language="dart")
        source = "// This is a comment\nclass Foo { /* block */ int x; }"
        result = c.compress(source, "Review.")
        # Comments should be gone in the compressed source
        assert "This is a comment" not in result.compressed_source
        assert "block" not in result.compressed_source


class TestCompressorDartBloc:
    def test_compresses_repeated_identifier(self, comp):
        source = """\
class UserBloc extends Bloc<UserEvent, UserState> {
  final UserRepository _repo;
  UserBloc({required UserRepository repo}) : _repo = repo, super(UserInitial()) {
    on<LoadUser>(_onLoadUser);
    on<UpdateUser>(_onUpdateUser);
    on<DeleteUser>(_onDeleteUser);
  }
  Future<void> _onLoadUser(LoadUser event, Emitter<UserState> emit) async {
    emit(UserLoading());
    final result = await _repo.getUser(event.id);
    result.fold(
      (failure) => emit(UserError(failure: failure)),
      (user) => emit(UserLoaded(user: user)),
    );
  }
  Future<void> _onUpdateUser(UpdateUser event, Emitter<UserState> emit) async {
    emit(UserLoading());
    final result = await _repo.updateUser(event.user);
    result.fold(
      (failure) => emit(UserError(failure: failure)),
      (user) => emit(UserLoaded(user: user)),
    );
  }
  Future<void> _onDeleteUser(DeleteUser event, Emitter<UserState> emit) async {
    emit(UserLoading());
    final result = await _repo.deleteUser(event.id);
    result.fold(
      (failure) => emit(UserError(failure: failure)),
      (_) => emit(UserDeleted()),
    );
  }
}"""
        result = comp.compress(source, "Review this Bloc for issues.")
        # Should detect at least some repeated patterns
        assert result.stats.phrases_detected > 0
        # Compressed source should be shorter in characters
        assert len(result.compressed_source) < len(source)

    def test_no_negative_savings_reported(self, comp):
        source = "UserBloc UserBloc UserBloc UserBloc"
        result = comp.compress(source, "Review.")
        assert result.stats.net_token_savings >= 0

    def test_dictionary_contains_only_source_terms(self, comp):
        source = "class UserBloc extends UserRepository { UserBloc(UserRepository r); }"
        result = comp.compress(source, "Review.")
        for entry in result.dictionary.entries:
            # Each original phrase must appear in the source
            assert entry.original in source


class TestCompressorTypeScript:
    def test_typescript_component(self, comp, sample_typescript):
        result = comp.compress(sample_typescript, "Review this React component.")
        assert result.stats.original_tokens > 0
        # No crash; the compressed prompt should still mention the task
        assert "Review this React component." in result.compressed_prompt
