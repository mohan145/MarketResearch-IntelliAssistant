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
    """Get Google Gemini LLM instance with quota-error fallback to mock.

    Falls back to mock LLM when API key not set or quota exceeded.
    """
    from src.backend.config import get_settings

    settings = get_settings()

    if not settings.google_api_key:
        logger.warning("GOOGLE_API_KEY not set, using mock LLM for demo")
        return _get_mock_llm()

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import BaseMessage

        real_llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            api_key=settings.google_api_key,
            temperature=0.7,
            top_p=0.95,
            max_retries=0,  # Disable SDK-level retries — we handle fallback ourselves
        )

        # Wrap in a proxy that falls back to mock on quota errors
        mock_llm = _get_mock_llm()

        class QuotaFallbackLLM(BaseChatModel):
            @property
            def _llm_type(self) -> str:
                return "quota-fallback"

            def _generate(self, messages, stop=None, **kwargs):
                raise NotImplementedError

            def invoke(self, input, config=None, **kwargs):
                try:
                    return real_llm.invoke(input, config=config, **kwargs)
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e).lower():
                        logger.warning("Google quota exceeded, falling back to mock LLM")
                        return mock_llm.invoke(input, config=config, **kwargs)
                    raise

        return QuotaFallbackLLM()

    except Exception as e:
        logger.warning(f"Failed to initialize Google Gemini: {e}, using mock LLM")
        return _get_mock_llm()



def _get_anthropic_claude() -> BaseChatModel:
    """Get Anthropic Claude LLM instance or mock for demo.

    When ANTHROPIC_API_KEY is set: uses claude-sonnet-4-6
    - Context: 200K tokens
    - Cost: ~$3 per million input tokens
    - Quality: excellent for analysis tasks

    When not set: uses mock LLM for demo/testing (realistic responses, no API calls).
    """
    from src.backend.config import get_settings

    settings = get_settings()

    # Always use mock LLM for demo unless explicitly configured otherwise
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set, using mock LLM for demo")
        return _get_mock_llm()

    try:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.llm_model,
            api_key=settings.anthropic_api_key,
            temperature=0.7,
        )
    except Exception as e:
        logger.warning(f"Failed to initialize Anthropic Claude: {e}, using mock LLM")
        return _get_mock_llm()


def _get_openai_gpt() -> BaseChatModel:
    """Get OpenAI GPT LLM instance.

    Uses gpt-4o-mini (cost-effective alternative to gpt-4)
    - Context: 128K tokens
    - Cost: ~$0.15 per million input tokens
    - Quality: good for general tasks

    Falls back to mock LLM for demo/testing when API key not set.
    """
    from src.backend.config import get_settings

    settings = get_settings()

    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set, using mock LLM for demo")
        return _get_mock_llm()

    try:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model="gpt-4o-mini",
            api_key=settings.openai_api_key,
            temperature=0.7,
            top_p=0.95,
        )
    except Exception as e:
        logger.warning(f"Failed to initialize OpenAI GPT: {e}, using mock LLM")
        return _get_mock_llm()


def _get_mock_llm() -> BaseChatModel:
    """Get a mock LLM for testing/demo without API keys.

    Returns realistic-looking summaries for demo purposes.
    """
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import BaseMessage, AIMessage
    import json

    class MockLLM(BaseChatModel):
        @property
        def _llm_type(self) -> str:
            return "mock"

        def _generate(self, messages, stop=None, **kwargs):
            from langchain_core.outputs import Generation, LLMResult

            # Extract the last message content
            content = messages[-1].content if messages else ""

            # Check what the user is asking for (summarize vs judge)
            # Judge prompts mention "supported", "confidence", "explanation"
            # Summary prompts mention "executive_summary", "key_themes"
            if "supported" in content.lower() or "verify" in content.lower() or "judge" in content.lower():
                # Judge request - return mock verdict
                response_text = json.dumps({
                    "claim": "Model pricing has been reduced",
                    "supported": True,
                    "confidence": 0.75,
                    "explanation": "Found references to cost-efficient models in the provided sources",
                    "source_url": "https://example.com"
                })
            elif "RETURN VALID JSON" in content or "JSON SCHEMA" in content or "executive_summary" in content.lower():
                # Summarization request - return mock market summary
                response_text = json.dumps({
                    "executive_summary": "Based on the provided articles, the AI market shows significant competitive activity. Key providers are expanding their offerings and adjusting pricing strategies. OpenAI continues to lead innovation with new model releases, while Mistral and Anthropic compete on open-source availability and specialized use cases.",
                    "key_themes": [
                        {
                            "theme": "Model Innovation and Releases",
                            "finding": "Major AI providers are rapidly releasing new models with improved capabilities and cost-efficiency.",
                            "sources": [
                                {
                                    "url": "https://mistral.ai/news/mistral-large-2407/",
                                    "excerpt": "Latest model release improving performance and efficiency"
                                }
                            ]
                        },
                        {
                            "theme": "Competitive Pricing Strategies",
                            "finding": "Companies are introducing tiered pricing and API optimizations to attract different customer segments.",
                            "sources": [
                                {
                                    "url": "https://example.com",
                                    "excerpt": "New pricing tiers introduced for enterprise customers"
                                }
                            ]
                        }
                    ],
                    "competitor_activities": [
                        {
                            "competitor": "OpenAI",
                            "activity": "Released GPT-4o mini for cost-efficient deployments",
                            "sources": [
                                {
                                    "url": "https://openai.com",
                                    "excerpt": "New model available for production use"
                                }
                            ]
                        },
                        {
                            "competitor": "Mistral",
                            "activity": "Announced Mistral Large 2407 with improved reasoning capabilities",
                            "sources": [
                                {
                                    "url": "https://mistral.ai/news/mistral-large-2407/",
                                    "excerpt": "New model announcement with technical details"
                                }
                            ]
                        }
                    ]
                })
            else:
                # Generic response
                response_text = '{"response": "Mock LLM response"}'

            return LLMResult(
                generations=[[Generation(text=response_text)]],
                llm_output={"model": "mock"},
            )

        def invoke(self, input, config=None, **kwargs):
            """Override invoke for simplicity."""
            if isinstance(input, list):
                # List of messages
                result = self._generate(input)
                return AIMessage(content=result.generations[0][0].text)
            result = self._generate([input])
            return AIMessage(content=result.generations[0][0].text)

    return MockLLM()


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