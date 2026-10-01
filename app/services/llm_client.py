"""Hosted LLM Client interface supporting Groq and Google Gemini endpoints."""

import logging
from abc import ABC, abstractmethod
from typing import Optional
import httpx
from app.config import Settings

logger = logging.getLogger(__name__)


class LLMConfigurationError(Exception):
    """Raised when an LLM provider is improperly configured or missing credentials."""
    pass


class LLMAPIError(Exception):
    """Raised when the hosted LLM API returns an error response."""
    pass


class BaseLLMClient(ABC):
    """Abstract base class for hosted LLM providers."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Check whether credentials are provided."""
        pass

    @abstractmethod
    async def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 1024) -> str:
        """Call hosted LLM endpoint with prompt and return generated text."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name."""
        pass


class GroqLLMClient(BaseLLMClient):
    """Hosted LLM Client for Groq (OpenAI-compatible API)."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile", timeout_seconds: float = 20.0):
        self.api_key = api_key.strip()
        self.model = model
        self.timeout = timeout_seconds
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"

    @property
    def provider_name(self) -> str:
        return f"Groq ({self.model})"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key != "your_groq_api_key_here")

    async def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 1024) -> str:
        if not self.is_configured():
            raise LLMConfigurationError(
                "Groq API key is missing. Please set GROQ_API_KEY in your .env file or environment variables."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.endpoint, headers=headers, json=payload)
                if response.status_code != 200:
                    err_msg = f"Groq API error ({response.status_code}): {response.text}"
                    logger.error(err_msg)
                    raise LLMAPIError(err_msg)
                
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
        except httpx.RequestError as e:
            logger.error(f"Network error connecting to Groq API: {e}")
            raise LLMAPIError(f"Network error contacting Groq hosted LLM: {str(e)}")


class GeminiLLMClient(BaseLLMClient):
    """Hosted LLM Client for Google Gemini AI Studio."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", timeout_seconds: float = 20.0):
        self.api_key = api_key.strip()
        self.model = model
        self.timeout = timeout_seconds

    @property
    def provider_name(self) -> str:
        return f"Google Gemini ({self.model})"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key != "your_gemini_api_key_here")

    async def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 1024) -> str:
        if not self.is_configured():
            raise LLMConfigurationError(
                "Gemini API key is missing. Please set GEMINI_API_KEY in your .env file or environment variables."
            )

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
                if response.status_code != 200:
                    err_msg = f"Gemini API error ({response.status_code}): {response.text}"
                    logger.error(err_msg)
                    raise LLMAPIError(err_msg)
                
                result = response.json()
                candidates = result.get("candidates", [])
                if not candidates:
                    raise LLMAPIError("No response candidates returned by Gemini.")
                return candidates[0]["content"]["parts"][0]["text"].strip()
        except httpx.RequestError as e:
            logger.error(f"Network error connecting to Gemini API: {e}")
            raise LLMAPIError(f"Network error contacting Gemini hosted LLM: {str(e)}")


def create_llm_client(settings: Settings) -> BaseLLMClient:
    """Factory creating the appropriate hosted LLM client according to settings."""
    provider = settings.resolved_llm_provider
    if provider == "gemini":
        return GeminiLLMClient(api_key=settings.gemini_api_key, model=settings.gemini_model)
    return GroqLLMClient(api_key=settings.groq_api_key, model=settings.groq_model)
