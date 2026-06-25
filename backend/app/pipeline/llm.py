from collections.abc import AsyncIterator
from typing import Any

from ollama import AsyncClient

from app.core.config import settings


class LLMAdapter:
    """Thin async wrapper around a local Ollama model."""

    def __init__(self, model: str | None = None, host: str | None = None):
        self.model = model or settings.OLLAMA_MODEL
        self.client = AsyncClient(host=host or settings.OLLAMA_BASE_URL)

    def _messages(self, prompt: str, system: str) -> list[dict[str, str]]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def complete(
        self,
        prompt: str,
        system: str = "",
        format: Any | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Return a full completion. Pass `format` (a JSON schema) for structured output."""
        response = await self.client.chat(
            model=self.model,
            messages=self._messages(prompt, system),
            format=format,
            options={"temperature": temperature},
        )
        return response.message.content or ""

    async def stream(self, prompt: str, system: str = "") -> AsyncIterator[str]:
        """Yield content tokens as they are generated (used by the live interview loop)."""
        async for chunk in await self.client.chat(
            model=self.model,
            messages=self._messages(prompt, system),
            stream=True,
        ):
            token = chunk.message.content
            if token:
                yield token


if __name__ == "__main__":
    import asyncio

    async def _smoke():
        llm = LLMAdapter()
        print("complete:", await llm.complete("Say hello in exactly one short sentence."))
        print("stream:", end=" ")
        async for tok in llm.stream("Count from 1 to 5."):
            print(tok, end="", flush=True)
        print()

    asyncio.run(_smoke())
