import logging
from functools import lru_cache

from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


def get_llm(provider: str | None = None) -> BaseChatModel:
    """Return a configured LLM instance for the given provider.

    Provider is resolved from (in order):
    1. The provider argument
    2. LLM_PROVIDER env var
    3. Default: "google"

    Raises:
        ValueError: Unknown provider name.
        RuntimeError: API key not set for the requested provider.
        ImportError: Provider's langchain package is not installed.
    """
    from src.backend.config import get_settings

    settings = get_settings()
    provider = (provider or settings.llm_provider).lower()

    logger.info("Loading LLM provider: %s / %s", provider, settings.llm_model)

    if provider == "google":
        return _get_google_gemini()
    elif provider == "anthropic":
        return _get_anthropic_claude()
    elif provider == "openai":
        return _get_openai_gpt()
    else:
        raise ValueError(
            f"Unknown LLM provider '{provider}'. "
            "Supported values: google, anthropic, openai"
        )


def _get_google_gemini() -> BaseChatModel:
    from src.backend.config import get_settings

    settings = get_settings()

    if not settings.google_api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. "
            "Add it to your .env file or Azure Container Apps secrets."
        )

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        raise ImportError(
            "langchain-google-genai is not installed. "
            "Run: pip install langchain-google-genai"
        )

    return ChatGoogleGenerativeAI(
        model=settings.llm_model,
        api_key=settings.google_api_key,
        temperature=0.7,
        top_p=0.95,
        max_retries=2,
    )


def _get_anthropic_claude() -> BaseChatModel:
    from src.backend.config import get_settings

    settings = get_settings()

    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. "
            "Add it to your .env file or Azure Container Apps secrets."
        )

    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        raise ImportError(
            "langchain-anthropic is not installed. "
            "Run: pip install langchain-anthropic"
        )

    return ChatAnthropic(
        model=settings.llm_model,
        api_key=settings.anthropic_api_key,
        temperature=0.7,
    )


def _get_openai_gpt() -> BaseChatModel:
    from src.backend.config import get_settings

    settings = get_settings()

    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. "
            "Add it to your .env file or Azure Container Apps secrets."
        )

    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError(
            "langchain-openai is not installed. "
            "Run: pip install langchain-openai"
        )

    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=0.7,
        top_p=0.95,
    )


# Cache keyed by "provider:model" — prevents stale instances when config changes
_llm_cache: dict[str, BaseChatModel] = {}


def get_llm_cached(provider: str | None = None) -> BaseChatModel:
    """Return a cached LLM instance, creating it on first call.

    Cache key includes both provider and model name so a config change
    (e.g. switching LLM_MODEL in .env) invalidates the cached instance.

    Raises:
        RuntimeError: If the API key for the provider is not configured.
    """
    from src.backend.config import get_settings

    settings = get_settings()
    provider = (provider or settings.llm_provider).lower()
    cache_key = f"{provider}:{settings.llm_model}"

    if cache_key not in _llm_cache:
        _llm_cache[cache_key] = get_llm(provider)
        logger.debug("Cached LLM instance: %s", cache_key)

    return _llm_cache[cache_key]
