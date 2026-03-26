# app/config.py

import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # DeepInfra
    deepinfra_api_key: str = ""
    deepinfra_model: str = "meta-llama/Llama-3.2-11B-Vision-Instruct"

    # Database
    database_url: str = ""

    # Africa's Talking
    at_username: str = ""
    at_api_key: str = ""
    at_sandbox: bool = True

    # Scraper
    scraper_interval_hours: int = 6

    # App
    log_level: str = "INFO"


settings = Settings()