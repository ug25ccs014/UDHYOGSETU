"""LLM provider abstraction.

The application talks to a single ``LLMProvider`` interface. Concrete
implementations for Google Gemini, Groq and local Ollama model servers all
implement this same interface, so swapping providers never touches the rest of
the codebase.

A fallback chain (primary -> secondary -> local) keeps the system operational
even if one hosted provider is unreachable. Failures are never surfaced raw to
users by the caller; this layer logs and degrades gracefully.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Base interface every LLM provider implements."""

    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """Whether the provider has the configuration needed to run."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        """Generate a complete (non-streamed) response."""

    async def structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Return a structured (JSON) result. Providers may override with
        prompt-based JSON extraction; base implementation wraps ``generate``."""
        text = await self.generate(system_prompt, user_prompt, temperature=temperature)
        return self._parse_json(text)

    async def stream(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        """Stream a response token-by-token. Default yields the full value."""
        text = await self.generate(system_prompt, user_prompt)
        yield text

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        import json
        text = text.strip()
        # Strip markdown code fences if present.
        if text.startswith("```"):
            text = text.strip("`")
            text = text.removeprefix("json")
            text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find the first {...} block.
            import re
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            return {"raw": text, "error": "Failed to parse structured output"}


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        import httpx
        self._httpx = httpx
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or "gemini-1.5-flash"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(self, system_prompt, user_prompt, temperature=0.2, max_tokens=1024) -> str:
        url = f"{self.base_url}/models/{self.model}:generateContent"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}],
                }
            ],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        async with self._httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError):
            return "I could not generate a response from the Gemini model."


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        import httpx
        self._httpx = httpx
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or "llama-3.1-8b-instant"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(self, system_prompt, user_prompt, temperature=0.2, max_tokens=1024) -> str:
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with self._httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return "I could not generate a response from the Groq model."


class OllamaProvider(LLMProvider):
    """Local model server via the standard Ollama HTTP API."""

    name = "ollama"

    def __init__(self, base_url: str | None = None, model: str | None = None):
        import httpx
        self._httpx = httpx
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or "llama3.2"

    def is_available(self) -> bool:
        return True  # Local; availability is probed at call time.

    async def generate(self, system_prompt, user_prompt, temperature=0.2, max_tokens=1024) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        async with self._httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data.get("response", "")


class MockLLMProvider(LLMProvider):
    """Deterministic provider used when no hosted/local model is configured.

    It never invents content: it extracts a grounded answer directly from the
    retrieved context, so the copilot remains safe and deterministic on maker
    machines with no API keys.
    """

    name = "mock"

    def __init__(self, *args, **kwargs):
        pass

    def is_available(self) -> bool:
        return True

    async def generate(self, system_prompt, user_prompt, temperature=0.2, max_tokens=1024) -> str:
        # Heuristic: pull the most relevant sentence from the context block.
        lines = [ln.strip() for ln in user_prompt.splitlines() if ln.strip()]
        context_lines = [
            ln for ln in lines
            if not ln.lower().startswith(("question", "answer", "source"))
            and len(ln) > 30
        ]
        if context_lines:
            return context_lines[0]
        return "I could not find sufficient authoritative information to answer this question."


_PROVIDER_REGISTRY = {
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "ollama": OllamaProvider,
    "mock": MockLLMProvider,
}


class LLMProviderFactory:
    """Builds providers and a fallback chain configured by ``LLM_PROVIDER``."""

    @classmethod
    def create(cls, name: str | None = None) -> LLMProvider:
        name = name or settings.DEFAULT_LLM_PROVIDER
        name = name.lower()
        provider_cls = _PROVIDER_REGISTRY.get(name, MockLLMProvider)
        try:
            provider = provider_cls()
        except Exception as exc:  # noqa: BLE001 - provider build can fail on external SDK state
            logger.warning("Failed to build %s provider: %s", name, exc)
            provider = MockLLMProvider()
        return provider

    @classmethod
    def fallback_chain(cls) -> list[LLMProvider]:
        """Primary provider plus fallbacks, ending in the safe mock provider."""
        primary = cls.create(settings.DEFAULT_LLM_PROVIDER)
        chain: list[LLMProvider] = [primary]
        for alt in ("gemini", "groq", "ollama"):
            if alt != primary.name.lower():
                try:
                    chain.append(cls.create(alt))
                except Exception as exc:  # noqa: BLE001 - fallback chain is best-effort
                    logger.debug("Alternative provider %s unavailable: %s", alt, exc)
                    continue
        chain.append(MockLLMProvider())
        # De-duplicate while preserving order.
        seen = set()
        deduped = []
        for p in chain:
            key = type(p).__name__
            if key not in seen and p.is_available():
                deduped.append(p)
                seen.add(key)
        if not any(isinstance(p, MockLLMProvider) for p in deduped):
            deduped.append(MockLLMProvider())
        return deduped


async def generate_with_fallback(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> str:
    """Try each provider in the fallback chain and return the first success."""
    for provider in LLMProviderFactory.fallback_chain():
        try:
            if not provider.is_available() and provider.name != "mock":
                continue
            return await provider.generate(system_prompt, user_prompt, temperature, max_tokens)
        except Exception as exc:  # noqa: BLE001 - external LLM calls raise unpredictably
            logger.warning("LLM provider %s failed, trying next: %s", provider.name, exc)
    return "I could not generate a response. Please try again later."