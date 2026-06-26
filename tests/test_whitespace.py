"""Tests for the WhitespaceNormalizer phase."""
import pytest

from llmpress.phases.whitespace import WhitespaceNormalizer


@pytest.fixture()
def normalizer():
    return WhitespaceNormalizer()


def test_trailing_whitespace_removed(normalizer):
    result = normalizer.apply("hello   \nworld   ")
    for line in result.split("\n"):
        assert not line.endswith(" "), f"Line still has trailing space: {line!r}"


def test_tabs_converted(normalizer):
    result = normalizer.apply("class Foo {\n\tvoid bar() {}\n}")
    assert "\t" not in result


def test_crlf_normalised(normalizer):
    result = normalizer.apply("line1\r\nline2\r\nline3")
    assert "\r" not in result
    assert result.count("\n") == 2


def test_internal_spaces_collapsed(normalizer):
    result = normalizer.apply("void  foo()  {}")
    assert "  " not in result


def test_indentation_preserved(normalizer):
    code = "class Foo {\n  void bar() {\n    return 1;\n  }\n}"
    result = normalizer.apply(code)
    # Leading indentation must survive
    assert "  void bar" in result
    assert "    return 1" in result


def test_multiple_blank_lines_collapsed(normalizer):
    code = "line1\n\n\n\n\nline2"
    result = normalizer.apply(code)
    assert "\n\n\n" not in result


def test_single_blank_line_preserved(normalizer):
    code = "line1\n\nline2"
    result = normalizer.apply(code)
    assert "\n\n" in result


def test_no_collapse_blank_lines(normalizer):
    n = WhitespaceNormalizer(collapse_blank_lines=False)
    code = "a\n\n\n\nb"
    result = n.apply(code)
    # With flag off, multiple blanks are preserved
    assert "\n\n\n" in result


def test_empty_string(normalizer):
    assert normalizer.apply("") == ""


def test_already_clean_unchanged(normalizer):
    code = "class Foo {\n  void bar() {}\n}"
    result = normalizer.apply(code)
    assert result == code
