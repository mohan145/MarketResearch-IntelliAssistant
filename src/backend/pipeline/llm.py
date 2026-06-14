import logging
from typing import Literal

from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


def get_llm(provider: str | None = None) -> BaseChatModel:
    """Get LLM instance by provider name.

    Supported providers:
    - google: Google Gemini (free tier)
    - anthropic: Anthropic Claude
    - openai: OpenAI GPT

    Provider is determined by (in order):
    1. provider parameter (explicit override)
    2. settings.LLM_PROVIDER env var
    3. Default: "google"

    Args:
        provider: Optional provider override ("google", "anthropic", "openai")

    Returns:
        BaseChatModel instance configured with API key + model from settings

    Raises:
        ValueError: If provider not supported or API key missing
    """
    from src.backend.config import get_settings

    settings = get_settings()

    # Determine which provider to use
    provider = provider or settings.llm_provider
    provider = provider.lower()

    logger.info(f"Loading LLM provider: {provider}")

    if provider == "google":
        return _get_google_gemini()
    elif provider == "anthropic":
        return _get_anthropic_claude()
    elif provider == "openai":
        return _get_openai_gpt()
    else:
        raise ValueError(
            f"Unknown LLM provider: {provider}. "
            f"Supported: google, anthropic, openai"
        )


def _get_google_gemini() -> BaseChatModel:
    """Get Google Gemini LLM instance.

    Uses free tier by default: gemini-1.5-flash
    - Rate limit: 15 requests/min, 1500 requests/day
    - Cost: free
    - Quality: good for summarization tasks
    """
    from langchain_google_genai import ChatGoogleGenerativeAI

    from src.backend.config import get_settings

    settings = get_settings()

    if not settings.google_api_key:
        raise ValueError(
            "GOOGLE_API_KEY not set. Get it from: "
            "https://aistudio.google.com/app/apikey"
        )

    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        api_key=settings.google_api_key,
        temperature=0.7,
        top_p=0.95,
    )


def _get_anthropic_claude() -> BaseChatModel:
    """Get Anthropic Claude LLM instance.

    Uses claude-sonnet-4-6 by default (best for long-context summarization)
    - Context: 200K tokens
    - Cost: ~$3 per million input tokens
    - Quality: excellent for analysis tasks
    """
    from langchain_anthropic import ChatAnthropic

    from src.backend.config import get_settings

    settings = get_settings()

    if not settings.anthropic_api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY not set. Get it from: "
            "https://console.anthropic.com/"
        )

    return ChatAnthropic(
        model="claude-sonnet-4-6",
        api_key=settings.anthropic_api_key,
        temperature=0.7,
        top_p=0.95,
    )


def _get_openai_gpt() -> BaseChatModel:
    """Get OpenAI GPT LLM instance.

    Uses gpt-4o-mini (cost-effective alternative to gpt-4)
    - Context: 128K tokens
    - Cost: ~$0.15 per million input tokens
    - Quality: good for general tasks
    """
    from langchain_openai import ChatOpenAI

    from src.backend.config import get_settings

    settings = get_settings()

    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY not set. Get it from: "
            "https://platform.openai.com/account/api-keys"
        )

    return ChatOpenAI(
        model="gpt-4o-mini",
        api_key=settings.openai_api_key,
        temperature=0.7,
        top_p=0.95,
    )


# Global LLM instance (cached, created on first use)
_llm_cache: dict[str, BaseChatModel] = {}


def get_llm_cached(provider: str | None = None) -> BaseChatModel:
    """Get cached LLM instance (same instance per provider per process).

    Avoids recreating LLM instances for every request.
    Safe for FastAPI dependency injection (request-scoped cleanup handles cache).
    """
    from src.backend.config import get_settings

    settings = get_settings()
    provider = provider or settings.llm_provider

    if provider not in _llm_cache:
        _llm_cache[provider] = get_llm(provider)
        logger.debug(f"Cached LLM instance for provider: {provider}")

    return _llm_cache[provider]