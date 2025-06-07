from pydantic_settings import BaseSettings, SettingsConfigDict # Added SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Project"
    DATABASE_URL: str # Type will be inferred from .env
    API_V1_STR: str = "/api/v1"

    # JWT settings - these will be loaded from .env or use defaults
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

    # Logging configuration
    LOG_LEVEL: str = "INFO"  # Default log level, can be overridden by .env

    # Email verification settings
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24 # Default to 24 hours

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra='ignore')

settings = Settings()
