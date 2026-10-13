"""Обёртка над LLM. Основной провайдер - Anthropic Claude через LangChain.

Переменные окружения (см. .env.example):
    LLM_PROVIDER   anthropic | openai | ollama   (по умолчанию anthropic)
    LLM_MODEL      id модели провайдера
    ANTHROPIC_API_KEY / OPENAI_API_KEY / OLLAMA_BASE_URL
"""
from __future__ import annotations

import os

from langchain_core.messages import HumanMessage, SystemMessage

DEFAULTS = {
    "anthropic": "claude-haiku-5-5",
    "openai": "gpt-4o-mini",
    "ollama": "llama3.1:8b",
}


def make_llm(provider: str | None = None, model: str | None = None, temperature: float = 0.0):
    provider = (provider or os.getenv("LLM_PROVIDER", "anthropic")).lower()
    model = model or os.getenv("LLM_MODEL") or DEFAULTS[provider]
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        # у новых моделей Claude параметр temperature объявлен устаревшим - не передаём
        return ChatAnthropic(model=model, max_tokens=1500)
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, temperature=temperature)
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model, temperature=temperature,
                          base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    raise ValueError(f"Неизвестный провайдер LLM: {provider}")


class LLM:
    def __init__(self, provider: str | None = None, model: str | None = None):
        self.client = make_llm(provider, model)
        self.model = getattr(self.client, "model", None) or getattr(self.client, "model_name", "?")

    def complete(self, system: str, user: str) -> str:
        resp = self.client.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        content = resp.content
        if isinstance(content, list):  # Anthropic может вернуть список блоков
            content = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
        return content.strip()
