from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "MedNarrate"
    app_env: str = "development"
    debug: bool = False
    api_prefix: str = "/api"
    frontend_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/mednarrate"
    auto_create_tables: bool = True

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    cookie_name: str = "mednarrate_access"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cookie_domain: str | None = None
    csrf_cookie_name: str = "mednarrate_csrf"

    llm_provider: str = "mock"
    gemini_api_key: str = ""
    gemini_models: str = "gemini-3.8-flash,gemini-3.7-flash,gemini-3.5-flash-lite"
    @property
    def gemini_model_list(self) -> list[str]:
        return [
            model.strip()
            for model in self.gemini_models.split(",")
            if model.strip()
        ]

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    rag_top_k: int = 4
    rag_score_threshold: float = 0.42
    rag_min_local_chunks: int = 2
    rag_report_max_chunks: int = 14

    online_rag_enabled: bool = True
    web_search_provider: str = "tavily"
    tavily_api_key: str = ""
    online_rag_max_results: int = 4
    online_rag_search_depth: str = "advanced"
    trusted_medical_domains: str = "medlineplus.gov,nih.gov,nlm.nih.gov,cdc.gov,who.int,nhs.uk,msdmanuals.com"
    dynamic_kb_cache_enabled: bool = True

    ocr_enabled: bool = True
    ocr_min_confidence: float = 0.45
    ocr_pdf_dpi: int = 180
    max_pdf_ocr_pages: int = 20

    persist_results: bool = True
    max_upload_mb: int = 15
    max_extracted_chars: int = 80_000

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        values = [item.strip() for item in self.cors_origins.split(",") if item.strip()]
        if self.frontend_url and self.frontend_url not in values:
            values.append(self.frontend_url)
        return values

    @property
    def trusted_medical_domain_list(self) -> list[str]:
        return [item.strip().lower() for item in self.trusted_medical_domains.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
