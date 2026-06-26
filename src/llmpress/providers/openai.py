from __future__ import annotations

DEFAULT_MODEL = "gpt-4o"


class OpenAIProvider:
    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = 4096) -> None:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "The 'openai' package is required for llmpress run --provider openai.\n"
                "Install it with:  python3 -m pip install 'llmpress[openai]'"
            )
        self._client = OpenAI()
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
