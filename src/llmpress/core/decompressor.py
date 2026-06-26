from __future__ import annotations

import json
from pathlib import Path

from ..core.models import Dictionary
from ..phases import Expander


class Decompressor:
    """
    Expand aliases in an LLM response back to human-readable form.

    The compressor embeds ``[LLMPRESS:DICT]`` … ``[END:DICT]`` in the prompt
    it sends to the model.  Well-behaved models echo aliases back in their
    responses; this class resolves every alias to its original text.
    """

    def __init__(self) -> None:
        self._expander = Expander()

    def expand(self, text: str, dictionary: Dictionary) -> str:
        return self._expander.expand(text, dictionary)

    def expand_file(self, response_path: Path, dictionary_path: Path) -> str:
        text = response_path.read_text(encoding="utf-8")
        data = json.loads(dictionary_path.read_text(encoding="utf-8"))
        dictionary = Dictionary.from_dict(data)
        return self.expand(text, dictionary)
