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


def test_blank_lines_removed(normalizer):
    code = "line1\n\nline2\n\n\nline3"
    result = normalizer.apply(code)
    assert "\n\n" not in result
    assert result == "line1\nline2\nline3"


def test_blank_lines_between_methods_removed(normalizer):
    code = "void foo() {}\n\nvoid bar() {}"
    result = normalizer.apply(code)
    assert result == "void foo() {}\nvoid bar() {}"


def test_spaces_inside_parens_removed(normalizer):
    assert normalizer.apply("foo( a, b )") == "foo(a, b)"


def test_spaces_inside_brackets_removed(normalizer):
    assert normalizer.apply("list[ 0 ]") == "list[0]"


def test_space_before_comma_removed(normalizer):
    assert normalizer.apply("foo(a , b , c)") == "foo(a, b, c)"


def test_compound_operators_stripped(normalizer):
    assert normalizer.apply("x == y") == "x==y"
    assert normalizer.apply("x != y") == "x!=y"
    assert normalizer.apply("x => y") == "x=>y"
    assert normalizer.apply("x += 1") == "x+=1"
    assert normalizer.apply("x && y") == "x&&y"


def test_single_operators_stripped(normalizer):
    assert normalizer.apply("x = y") == "x=y"
    assert normalizer.apply("x + y") == "x+y"
    assert normalizer.apply("x - y") == "x-y"


def test_unary_minus_preserved(normalizer):
    # unary minus has no space on the left — must not be touched
    assert normalizer.apply("return -1;") == "return -1;"


def test_empty_string(normalizer):
    assert normalizer.apply("") == ""


def test_no_indentation_unchanged(normalizer):
    code = "foo()\nbar()\nbaz()"
    result = normalizer.apply(code)
    assert result == code
