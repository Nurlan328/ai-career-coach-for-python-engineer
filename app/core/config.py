"""Application settings, loaded from environment / .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_name: str = "AI Career Coach for Python Backend Engineers"
    debug: bool = True
    api_prefix: str = "/api"
    cors_origins: list[str] = ["*"]

    # --- Database ---
    # Default: zero-setup SQLite. Switch to Postgres via .env, e.g.
    #   postgresql+asyncpg://user:pass@localhost:5432/career_coach
    database_url: str = "sqlite+aiosqlite:///./career_coach.db"
    # Dev convenience: create tables on startup. Set False to let Alembic own the
    # schema (then run `alembic upgrade head`).
    auto_create_tables: bool = True

    # --- Security / JWT ---
    secret_key: str = "dev-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24h

    # --- LLM (Claude) ---
    anthropic_api_key: str | None = None
    # Override with claude-opus-4-8 for max quality, or claude-haiku-4-5 for speed/cost.
    llm_model: str = "claude-sonnet-4-6"
    llm_max_tokens: int = 2000

    # --- Background jobs (Celery) + cache (Redis) ---
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None  # defaults to redis_url
    celery_result_backend: str | None = None  # defaults to redis_url
    celery_task_always_eager: bool = False  # True in tests: run tasks inline
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600

    # --- RAG (knowledge base) ---
    # Multilingual (RU+EN) embedding model served via fastembed.
    rag_embed_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    rag_top_k: int = 4

    # --- Billing (Stripe) ---
    # Leave the secret empty to run billing in mock mode (instant upgrade, no charge).
    # Real mode needs all three: STRIPE_SECRET_KEY + STRIPE_PRICE_PRO (recurring
    # price id) + STRIPE_WEBHOOK_SECRET (whsec_..., from `stripe listen` or the
    # dashboard endpoint).
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_pro: str | None = None
    # Pin the Stripe API version so a server-side upgrade can't change payload
    # shapes under us. None = whatever the installed SDK defaults to.
    stripe_api_version: str | None = None
    billing_success_url: str = "http://localhost:5173/billing?status=success"
    billing_cancel_url: str = "http://localhost:5173/billing?status=cancel"
    # Where the Stripe-hosted customer portal sends the user back to.
    billing_portal_return_url: str = "http://localhost:5173/billing"
    free_interviews_per_month: int = 3
    pro_price_usd: float = 19.0

    # --- Uploads ---
    max_upload_mb: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
