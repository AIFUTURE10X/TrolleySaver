from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://grocery:grocery123@localhost:5433/grocery_prices"

    # Application
    environment: str = "development"
    secret_key: str = "change-this-in-production"
    api_prefix: str = "/api"

    # JWT Authentication
    jwt_secret_key: str = "jwt-secret-change-in-production"

    # Stripe (for subscriptions)
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_monthly: str | None = None  # price_xxx from Stripe dashboard
    stripe_price_yearly: str | None = None   # price_xxx from Stripe dashboard

    # Email (optional)
    sendgrid_api_key: str | None = None
    from_email: str = "alerts@grocerycompare.com"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Frontend URL (for redirects)
    frontend_url: str = "http://localhost:3000"

    # Firecrawl (for scraping specials)
    firecrawl_api_key: str | None = None

    # Admin API Key (for manual scrape triggers)
    admin_api_key: str | None = None

    class Config:
        env_file = "C:/Projects/Supermarket Specials Compare/backend/.env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
