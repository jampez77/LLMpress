import re

from .base import Phase


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

        # Collapse 2+ consecutive blank lines to exactly one
        result = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
        return result.strip()
