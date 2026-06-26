"""Tests for the WhitespaceNormalizer phase."""
import pytest

from llmpress.phases.whitespace import WhitespaceNormalizer, _detect_indent_unit


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


def test_indentation_compressed_4_to_1(normalizer):
    code = "class Foo {\n    void bar() {\n        return 1;\n    }\n}"
    result = normalizer.apply(code)
    lines = result.split("\n")
    # 4-space indent → 1 space per level
    assert lines[1].startswith(" void")
    assert lines[2].startswith("  return")
    assert lines[3].startswith(" }")


def test_indentation_compressed_2_to_1(normalizer):
    code = "class Foo {\n  void bar() {\n    return 1;\n  }\n}"
    result = normalizer.apply(code)
    lines = result.split("\n")
    assert lines[1].startswith(" void")
    assert lines[2].startswith("  return")


def test_indentation_compressed_tabs(normalizer):
    code = "class Foo {\n\tvoid bar() {\n\t\treturn 1;\n\t}\n}"
    result = normalizer.apply(code)
    lines = result.split("\n")
    assert lines[1].startswith(" void")
    assert lines[2].startswith("  return")


def test_detect_indent_unit_4_spaces():
    lines = ["class Foo {", "    void bar() {", "        return;", "    }"]
    assert _detect_indent_unit(lines) == 4


def test_detect_indent_unit_2_spaces():
    lines = ["class Foo {", "  void bar() {", "    return;", "  }"]
    assert _detect_indent_unit(lines) == 2


def test_detect_indent_unit_no_indent():
    lines = ["foo()", "bar()"]
    assert _detect_indent_unit(lines) == 1


def test_multiple_blank_lines_collapsed(normalizer):
    code = "line1\n\n\nline2"
    result = normalizer.apply(code)
    assert "\n\n\n" not in result


def test_double_blank_lines_collapsed(normalizer):
    code = "line1\n\n\nline2"
    result = normalizer.apply(code)
    assert result == "line1\n\nline2"


def test_single_blank_line_preserved(normalizer):
    code = "line1\n\nline2"
    result = normalizer.apply(code)
    assert "\n\n" in result


def test_empty_string(normalizer):
    assert normalizer.apply("") == ""


def test_no_indentation_unchanged(normalizer):
    code = "foo()\nbar()\nbaz()"
    result = normalizer.apply(code)
    assert result == code
