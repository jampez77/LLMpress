from __future__ import annotations


class AnthropicProvider:
    def __init__(self, model: str = "claude-sonnet-4-6", max_tokens: int = 4096) -> None:
        try:
            import anthropic as _anthropic
        except ImportError:
            raise ImportError(
                "The 'anthropic' package is required for llmpress run.\n"
                "Install it with:  python3 -m pip install 'llmpress[anthropic]'"
            )
        self._client = _anthropic.Anthropic()
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, prompt: str) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
