"""LLM factory for creating language model instances."""

from langchain_anthropic import ChatAnthropic
from infrastructure.config.settings import settings
from core.constants import DefaultValues


def create_llm(model: str, temperature: float = DefaultValues.DEFAULT_TEMPERATURE) -> ChatAnthropic:
    return ChatAnthropic(
        temperature=temperature,
        model=model,
        api_key=settings.claude.api_key
    )


def create_supervisor_llm(temperature: float = DefaultValues.DEFAULT_TEMPERATURE) -> ChatAnthropic:
    return create_llm(settings.supervisor_model, temperature)


def create_agent_llm(temperature: float = DefaultValues.DEFAULT_TEMPERATURE) -> ChatAnthropic:
    return create_llm(settings.agent_model, temperature)
