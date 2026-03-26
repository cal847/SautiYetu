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

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()