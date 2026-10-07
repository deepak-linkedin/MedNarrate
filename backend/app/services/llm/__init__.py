from app.core.config import get_settings
from app.services.llm.base import LLMProvider
from app.services.llm.mock_provider import MockProvider


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()
    if provider == "mock":
        return MockProvider()
    if provider == "gemini":
        from app.services.llm.gemini_provider import GeminiProvider
        # return GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            models=settings.gemini_model_list,
        )
    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
