from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Central app configuration, loaded from environment variables / .env file.
    """
    database_url: str = "sqlite:///./forensics.db"
    geo_api_url: str = "http://ip-api.com/json/{ip}"
    frontend_origin: str = "http://localhost:5173"
    anthropic_api_key: str = ""

    class Config:
        env_file = ".env"
        env_prefix = ""
        case_sensitive = False
        extra = "ignore"


settings = Settings()
