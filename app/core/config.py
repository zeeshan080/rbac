from pydantic_settings import BaseSettings, SettingsConfigDict # Added SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Project"
    DATABASE_URL: str # Type will be inferred from .env
    API_V1_STR: str = "/api/v1"

    # JWT settings - these will be loaded from .env or use defaults
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra='ignore')

settings = Settings()
