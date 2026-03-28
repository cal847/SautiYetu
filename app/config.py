# app/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional # Import Optional if needed for defaults


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/civic_intelligence"
    db_echo: bool = False

    # DeepInfra
    # Removed duplicate, using the one with default
    deepinfra_api_key: str = ""  
    deepinfra_model: str = "meta-llama/Meta-Llama-3.1-70B-Instruct"
    
    # Add the field that was causing the validation error if it's needed
    # Or remove it if it's not actually used anywhere else
    deepinfra_api_url: str = "https://api.deepinfra.com/" # Add this if the error was about this field

    # Africa's Talking
    at_username: str = ""
    at_api_key: str = ""
    at_sandbox: bool = True

    # Scraper
    scraper_interval_hours: int = 6

    # App
    log_level: str = "INFO"

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # Project
    project_name: str = "SautiYetu"
    version: str = "0.1.0"

    # Using model_config for Pydantic v2
    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()