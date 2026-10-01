"""Application configuration using Pydantic Settings."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Superhero API Configuration
    superhero_api_token: str = ""
    superhero_api_base_url: str = "https://superheroapi.com/api"

    # Hosted LLM Configuration
    llm_provider: Literal["groq", "gemini", "auto"] = "auto"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Dataset Directory
    dataset_dir: str = "data/mythology_and_legends"

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    @property
    def resolved_llm_provider(self) -> str:
        """Determines active LLM provider based on settings and available API keys."""
        if self.llm_provider in ("groq", "gemini"):
            return self.llm_provider
        # Auto mode: prioritize groq if key present, else gemini
        if self.groq_api_key.strip():
            return "groq"
        if self.gemini_api_key.strip():
            return "gemini"
        return "groq"

    @property
    def has_superhero_token(self) -> bool:
        return bool(self.superhero_api_token and self.superhero_api_token.strip() and self.superhero_api_token != "your_superhero_api_token_here")

    @property
    def has_llm_key(self) -> bool:
        if self.resolved_llm_provider == "groq":
            return bool(self.groq_api_key and self.groq_api_key.strip() and self.groq_api_key != "your_groq_api_key_here")
        return bool(self.gemini_api_key and self.gemini_api_key.strip() and self.gemini_api_key != "your_gemini_api_key_here")

    @property
    def absolute_dataset_path(self) -> Path:
        base = Path(__file__).resolve().parent.parent
        return base / self.dataset_dir


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton instance of application settings."""
    return Settings()
