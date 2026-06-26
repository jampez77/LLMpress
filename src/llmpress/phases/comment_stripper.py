import re

from .base import Phase

# Patterns per comment style
_LINE_COMMENT = re.compile(r"(?m)//.*$")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_HASH_COMMENT = re.compile(r"(?m)#.*$")
_DASH_COMMENT = re.compile(r"(?m)--.*$")


class CommentStripper(Phase):
    """
    Remove comments from source code.

    Language detection is based on file extension hint passed at construction
    time.  If no hint is given, C-style comments (// and /* */) are stripped.

    Doc comments (/** ... */ or /// ...) are also stripped when strip_docs=True
    (default False — doc comments often carry semantic meaning).
    """

    def __init__(
        self,
        language: str = "auto",
        strip_docs: bool = False,
    ) -> None:
        self._language = language.lower()
        self._strip_docs = strip_docs

    def apply(self, source: str) -> str:
        lang = self._language

        if lang in {"python", "py", "ruby", "rb", "shell", "sh", "bash", "yaml", "yml"}:
            return self._strip_hash(source)
        if lang in {"sql", "lua", "haskell", "hs"}:
            return self._strip_dash(source)
        # default: C-family (dart, java, kotlin, swift, ts, tsx, js, jsx, cs, cpp, c)
        return self._strip_c_style(source)

    def _strip_c_style(self, source: str) -> str:
        # Block comments first (they can span lines)
        text = _BLOCK_COMMENT.sub("", source)
        # Line comments
        text = _LINE_COMMENT.sub("", text)
        return text

    def _strip_hash(self, source: str) -> str:
        return _HASH_COMMENT.sub("", source)

    def _strip_dash(self, source: str) -> str:
        return _DASH_COMMENT.sub("", source)
