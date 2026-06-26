import re

from .base import Phase


class WhitespaceNormalizer(Phase):
    """
    Collapse redundant whitespace while preserving syntactic structure.

    Rules:
    - Trailing whitespace removed from every line
    - Runs of 2+ blank lines reduced to one blank line
    - Tab characters converted to spaces
    - Line endings normalised to \\n
    - Indentation preserved (just the leading run is kept; internal runs collapsed)
    """

    def __init__(self, collapse_blank_lines: bool = True) -> None:
        self._collapse_blank_lines = collapse_blank_lines

    def apply(self, source: str) -> str:
        # Normalise line endings and tabs
        text = source.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")

        lines: list[str] = []
        for line in text.split("\n"):
            # Strip trailing whitespace
            stripped = line.rstrip()
            # Collapse internal runs of spaces (but keep leading indentation)
            leading = len(stripped) - len(stripped.lstrip())
            indent = stripped[:leading]
            body = re.sub(r" {2,}", " ", stripped[leading:])
            lines.append(indent + body)

        result = "\n".join(lines)

        if self._collapse_blank_lines:
            # Replace 3+ consecutive newlines with exactly 2
            result = re.sub(r"\n{3,}", "\n\n", result)

        return result.strip()
