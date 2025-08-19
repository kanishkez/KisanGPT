from pydantic import BaseModel
from typing import Optional
from functools import lru_cache
"""
App configuration (GitHub-safe)
- Reads secrets from environment variables (.env in dev) using python-dotenv
- No hardcoded API keys
- Uses Google Gemini 2.5 Pro via LangChain; authentication is GEMINI_API_KEY

Usage:
    from app.config import settings
    print(settings.GEMINI_API_KEY)  # None if not set
    # settings.MODEL_NAME, settings.llm_auth_token(), ...
"""
import os
from functools import lru_cache
from typing import Optional

try:
    # Load .env for local/dev. No-op if file is absent.
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

class Settings:
    # --- Application ---
    APP_NAME: str = os.getenv("APP_NAME", "KisanGPT")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in {"1", "true", "yes", "on"}

    # --- API Keys (from env) ---
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    DATAGOV_API_KEY: Optional[str] = os.getenv("DATAGOV_API_KEY")
    OPENWEATHER_API_KEY: Optional[str] = os.getenv("OPENWEATHER_API_KEY")

    # --- Data.gov.in API Configuration ---
    DATAGOV_BASE_URL: str = os.getenv("DATAGOV_BASE_URL", "https://api.data.gov.in")
    DATAGOV_VERIFY_SSL: bool = os.getenv("DATAGOV_VERIFY_SSL", "true").lower() in {"1", "true", "yes", "on"}

    # --- Specific API Endpoints ---
    MARKET_PRICES_ENDPOINT: str = os.getenv("MARKET_PRICES_ENDPOINT", "/resource/9ef84268-d588-465a-a308-a864a43d0070")
    WEATHER_DATA_ENDPOINT: str = os.getenv("WEATHER_DATA_ENDPOINT", "/resource/fd37f385-b9ae-4e59-8d4a-1c66e5202be3")
    CROP_PRODUCTION_ENDPOINT: str = os.getenv("CROP_PRODUCTION_ENDPOINT", "/resource/4178b5d3-94f9-4d20-b2a0-a47ad36f7151")

    # --- Database ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/database.db")

    # --- Cache Configuration ---
    CACHE_TTL_MINUTES: int = int(os.getenv("CACHE_TTL_MINUTES", "60"))

    # --- Data Refresh Intervals (in minutes) ---
    WEATHER_REFRESH_INTERVAL: int = int(os.getenv("WEATHER_REFRESH_INTERVAL", "60"))
    MARKET_REFRESH_INTERVAL: int = int(os.getenv("MARKET_REFRESH_INTERVAL", "120"))
    CROP_REFRESH_INTERVAL: int = int(os.getenv("CROP_REFRESH_INTERVAL", "1440"))  # 24 hours

    # --- LLM Configuration ---
    MODEL_PROVIDER: str = "gemini"
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gemini-2.0-flash-exp")

    # --- Helpers ---
    def require(self, name: str, value: Optional[str]) -> str:
        if not value:
            raise RuntimeError(f"Missing required environment variable: {name}")
        return value

    def llm_auth_token(self) -> str:
        # Use Gemini API key for the new LangChain implementation
        return self.require("GEMINI_API_KEY", self.GEMINI_API_KEY)
    
    def gemini_api_key(self) -> str:
        # Helper method to get Gemini API key
        return self.require("GEMINI_API_KEY", self.GEMINI_API_KEY)


@lru_cache()
def get_settings() -> Settings:
    return Settings()

 # Convenience import
settings = get_settings()