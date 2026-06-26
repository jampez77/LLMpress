"""Tests for the CLI."""
import json
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from llmpress.cli import compress, expand, main


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def dart_file(tmp_path):
    content = """\
class UserBloc extends Bloc<UserEvent, UserState> {
  final UserRepository _repo;
  UserBloc({required UserRepository repo}) : _repo = repo, super(UserInitial()) {
    on<LoadUser>(_onLoadUser);
    on<UpdateUser>(_onUpdateUser);
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
}"""
    f = tmp_path / "user_bloc.dart"
    f.write_text(content, encoding="utf-8")
    return f


# ── compress command ──────────────────────────────────────────────────────

class TestCompressCommand:
    def test_basic_compress(self, runner, dart_file, tmp_path):
        result = runner.invoke(compress, [
            str(dart_file), "Review this code.",
            "--output-dir", str(tmp_path),
            "--tokenizer", "approximate",
        ])
        assert result.exit_code == 0, result.output
        assert (tmp_path / "compressed_prompt.txt").exists()
        assert (tmp_path / "dictionary.json").exists()
        assert (tmp_path / "stats.json").exists()

    def test_compressed_prompt_contains_task(self, runner, dart_file, tmp_path):
        runner.invoke(compress, [
            str(dart_file), "Find all bugs.",
            "--output-dir", str(tmp_path),
            "--tokenizer", "approximate",
            "--quiet",
        ])
        content = (tmp_path / "compressed_prompt.txt").read_text()
        assert "Find all bugs." in content

    def test_dictionary_json_valid(self, runner, dart_file, tmp_path):
        runner.invoke(compress, [
            str(dart_file), "Review.",
            "--output-dir", str(tmp_path),
            "--tokenizer", "approximate",
            "--quiet",
        ])
        data = json.loads((tmp_path / "dictionary.json").read_text())
        assert "version" in data
        assert "aliases" in data

    def test_stats_json_valid(self, runner, dart_file, tmp_path):
        runner.invoke(compress, [
            str(dart_file), "Review.",
            "--output-dir", str(tmp_path),
            "--tokenizer", "approximate",
            "--quiet",
        ])
        data = json.loads((tmp_path / "stats.json").read_text())
        assert "original_tokens" in data
        assert "net_token_savings" in data

    def test_stats_only_no_files(self, runner, dart_file, tmp_path):
        out = tmp_path / "out"
        out.mkdir()
        runner.invoke(compress, [
            str(dart_file), "Review.",
            "--output-dir", str(out),
            "--tokenizer", "approximate",
            "--stats-only",
            "--quiet",
        ])
        assert not (out / "compressed_prompt.txt").exists()

    def test_prompt_from_file(self, runner, dart_file, tmp_path):
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Find performance issues.")
        result = runner.invoke(compress, [
            str(dart_file), str(prompt_file),
            "--output-dir", str(tmp_path),
            "--tokenizer", "approximate",
            "--quiet",
        ])
        assert result.exit_code == 0
        content = (tmp_path / "compressed_prompt.txt").read_text()
        assert "Find performance issues." in content


# ── expand command ────────────────────────────────────────────────────────

class TestExpandCommand:
    def _setup_expand(self, runner, dart_file, tmp_path):
        runner.invoke(compress, [
            str(dart_file), "Review.",
            "--output-dir", str(tmp_path),
            "--tokenizer", "approximate",
            "--quiet",
        ])
        return tmp_path / "dictionary.json"

    def test_expand_produces_output(self, runner, dart_file, tmp_path):
        dict_file = self._setup_expand(runner, dart_file, tmp_path)
        response_file = tmp_path / "response.txt"
        response_file.write_text("The T0 class looks good. T1 is used correctly.")

        result = runner.invoke(expand, [str(dict_file), str(response_file)])
        assert result.exit_code == 0

    def test_expand_aliases_replaced(self, runner, dart_file, tmp_path):
        dict_file = self._setup_expand(runner, dart_file, tmp_path)
        dict_data = json.loads(dict_file.read_text())
        aliases = list(dict_data["aliases"].keys())

        if not aliases:
            pytest.skip("No aliases produced for this fixture")

        alias = aliases[0]
        original = dict_data["aliases"][alias]
        response_file = tmp_path / "response.txt"
        response_file.write_text(f"The {alias} class is fine.")

        result = runner.invoke(expand, [str(dict_file), str(response_file)])
        assert result.exit_code == 0
        assert original in result.output

    def test_expand_to_file(self, runner, dart_file, tmp_path):
        dict_file = self._setup_expand(runner, dart_file, tmp_path)
        response_file = tmp_path / "response.txt"
        response_file.write_text("Looks good.")
        output_file = tmp_path / "expanded.txt"

        runner.invoke(expand, [
            str(dict_file), str(response_file),
            "--output", str(output_file),
            "--quiet",
        ])
        assert output_file.exists()


# ── llmpress group ────────────────────────────────────────────────────────

class TestMainGroup:
    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "compress" in result.output
        assert "expand" in result.output

    def test_compress_subcommand(self, runner, dart_file, tmp_path):
        result = runner.invoke(main, [
            "compress", str(dart_file), "Review.",
            "--output-dir", str(tmp_path),
            "--tokenizer", "approximate",
            "--quiet",
        ])
        assert result.exit_code == 0
