import re
from typing import List, Tuple

from .base import Phase

# Applied in order — compound operators before single chars to avoid
# partial matches (e.g. handle => before =, <= before <).
_OP_SUBS: List[Tuple[re.Pattern, str]] = [
    # spaces inside brackets
    (re.compile(r'\( +'),      '('),
    (re.compile(r' +\)'),      ')'),
    (re.compile(r'\[ +'),      '['),
    (re.compile(r' +\]'),      ']'),
    # space before comma / semicolon
    (re.compile(r' +([,;])'),  r'\1'),
    # compound operators
    (re.compile(r' *(=>|==|!=|<=|>=|\+=|-=|\*=|/=|&&|\|\||\?\?|->) *'), r'\1'),
    # single operators flanked by spaces on both sides
    (re.compile(r' ([=+\-*/%<>]) '), r'\1'),
]


def _strip_op_spaces(body: str) -> str:
    for pattern, repl in _OP_SUBS:
        body = pattern.sub(repl, body)
    return body


def _detect_indent_unit(lines: list) -> int:
    """Return the number of spaces per indent level (2 or 4).

    Uses a voting approach: whichever standard unit (4 then 2) explains at
    least 60% of indented lines wins.  This is robust against the occasional
    alignment or continuation line with an odd indent count that would drag a
    GCD-based approach down to 1.
    """
    counts = []
    for line in lines:
        if not line or line.isspace():
            continue
        stripped = line.lstrip(" ")
        spaces = len(line) - len(stripped)
        if spaces >= 2:
            counts.append(spaces)
    if not counts:
        return 1
    for unit in (4, 2):
        if sum(1 for c in counts if c % unit == 0) >= len(counts) * 0.6:
            return unit
    return 2


def _compress_indent(line: str, unit: int) -> str:
    """Re-emit the leading indent as 1 space per level."""
    if not line or line[0] != " ":
        return line
    stripped = line.lstrip(" ")
    spaces = len(line) - len(stripped)
    level = spaces // unit
    remainder = spaces % unit
    return " " * (level + remainder) + stripped


class WhitespaceNormalizer(Phase):
    """
    Normalise and minify whitespace for token-efficient LLM prompts.

    - Line endings normalised to \\n
    - Tabs expanded to 4 spaces, then indentation compressed to 1 space per level
    - Trailing whitespace removed from every line
    - Internal runs of spaces collapsed (leading indentation handled separately)
    - 2+ consecutive blank lines collapsed to one
    """

    def strip_operators(self, text: str) -> str:
        """Strip spaces around operators line-by-line, preserving indentation."""
        lines = []
        for line in text.split("\n"):
            leading = len(line) - len(line.lstrip(" "))
            indent = line[:leading]
            body = _strip_op_spaces(line[leading:])
            lines.append(indent + body)
        return "\n".join(lines)

    def apply(self, source: str) -> str:
        # Normalise line endings; expand tabs to 4 spaces before GCD detection
        text = source.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\t", "    ")

        raw_lines = text.split("\n")
        unit = _detect_indent_unit(raw_lines)

        lines = []
        for line in raw_lines:
            line = line.rstrip()
            line = _compress_indent(line, unit)
            leading = len(line) - len(line.lstrip(" "))
            indent = line[:leading]
            body = re.sub(r" {2,}", " ", line[leading:])
            lines.append(indent + body)

        # Remove all blank lines — they carry no semantic content for the LLM
        result = "\n".join(line for line in lines if line)
        return result.strip()
