from __future__ import annotations

import os
from typing import Any

import litellm


def _propagate_api_keys() -> None:
    """Propagate API keys from pydantic-settings into os.environ for LiteLLM.

    pydantic-settings reads .env into a Python object but does NOT set OS env
    vars. LiteLLM reads provider keys directly from os.environ, so we bridge
    the gap here without overwriting keys that were already set at process start.
    """
    try:
        from consent_engine.config import get_settings  # local import to avoid circular

        settings = get_settings()
        pairs = [
            ("GEMINI_API_KEY", settings.gemini_api_key),
            ("ANTHROPIC_API_KEY", settings.anthropic_api_key),
        ]
        for env_var, value in pairs:
            if value and not os.environ.get(env_var):
                os.environ[env_var] = value
    except Exception:  # noqa: BLE001
        pass


class LLMClient:
    """Thin LiteLLM wrapper. Swap `model` string to change LLM providers."""

    def __init__(self, model: str) -> None:
        self.model = model
        _propagate_api_keys()

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system: str | None = None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"model": self.model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        if system:
            kwargs["messages"] = [{"role": "system", "content": system}] + messages
        response = await litellm.acompletion(**kwargs)
        return dict(response)
