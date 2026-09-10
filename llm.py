"""
llm.py — model setup with one-line provider swapping.

The whole point of this file: `init_chat_model` lets you switch between OpenAI,
Anthropic, and others by changing a single string. In the MCP app we hard-wired
OpenAI; here the provider is a runtime choice. This is a core LangChain win.
"""

from __future__ import annotations

import os

from langchain.chat_models import init_chat_model

# Providers the UI offers. Add more by dropping a line here — init_chat_model
# supports many (google, groq, mistral, ollama, ...). Format: "provider:model".
PROVIDERS: dict[str, str] = {
    "OpenAI · gpt-4o-mini": "openai:gpt-4o-mini",
    "OpenAI · gpt-4o": "openai:gpt-4o",
    "Anthropic · Claude Sonnet": "anthropic:claude-sonnet-4-20250514",
}

DEFAULT_PROVIDER = "OpenAI · gpt-4o-mini"


def get_model(provider_label: str | None = None, temperature: float = 0):
    """
    Return a chat model for the chosen provider label.

    One line does what a provider-specific client would need many for — and the
    rest of the app never changes when you swap providers.
    """
    model_id = PROVIDERS.get(provider_label or DEFAULT_PROVIDER, PROVIDERS[DEFAULT_PROVIDER])
    provider = model_id.split(":", 1)[0]

    # friendly guard: tell the user which key is missing rather than a deep error
    key_env = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}.get(provider)
    if key_env and not os.getenv(key_env):
        raise RuntimeError(f"{key_env} is not set — needed for provider '{provider}'.")

    return init_chat_model(model_id, temperature=temperature)
