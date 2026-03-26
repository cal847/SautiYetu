from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/civic_intelligence"
    db_echo: bool = False

    # DeepInfra
    deepinfra_api_key: str = ""
    deepinfra_model: str = "meta-llama/Meta-Llama-3.1-70B-Instruct"

    # Africa's Talking
    at_username: str = ""
    at_api_key: str = ""
    at_sandbox: bool = True

    # Scraper
    scraper_interval_hours: int = 6

    # App
    log_level: str = "INFO"

<<<<<<< HEAD
=======
    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # Project
    project_name: str = "SautiYetu"
    version: str = "0.1.0"

    class Config:
        env_file = ".env"
        case_sensitive = False

>>>>>>> a1402789bc57b8fd4cdfae71d0567f78e2f049b6

settings = Settings()