"""
app/ai/client.py
-----------------
Thin async HTTP client for the DeepInfra inference API.

DeepInfra exposes an OpenAI-compatible /v1/chat/completions endpoint,
so we use httpx directly rather than pulling in the full OpenAI SDK.
"""

import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

DEEPINFRA_BASE_URL = "https://api.deepinfra.com/v1/openai"
REQUEST_TIMEOUT = 60  # seconds


class DeepInfraError(Exception):
    """Raised when the DeepInfra API returns a non-2xx response."""


class DeepInfraClient:
    """
    Async client for DeepInfra's OpenAI-compatible chat completions endpoint.

    Usage:
        async with DeepInfraClient() as client:
            text = await client.chat(prompt="Analyse this bill...")
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int = REQUEST_TIMEOUT,
    ) -> None:
        self._api_key = api_key or settings.deepinfra_api_key
        self._model = model or settings.deepinfra_model
        self._timeout = timeout
        self._http: httpx.AsyncClient | None = None

    # ── Context manager ───────────────────────────────────────────────────────

    async def __aenter__(self) -> "DeepInfraClient":
        self._http = httpx.AsyncClient(
            base_url=DEEPINFRA_BASE_URL,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=self._timeout,
        )
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    # ── Public API ────────────────────────────────────────────────────────────

    async def chat(
        self,
        prompt: str,
        *,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        """
        Send a single user prompt and return the assistant's reply as a string.

        Args:
            prompt:      The fully formatted user prompt.
            temperature: Low value keeps responses deterministic (default 0.1).
            max_tokens:  Upper bound on response length.

        Returns:
            The raw text content of the first completion choice.

        Raises:
            DeepInfraError: On non-2xx HTTP responses.
            httpx.TimeoutException: When the request exceeds `timeout` seconds.
        """
        if self._http is None:
            raise RuntimeError(
                "DeepInfraClient must be used as an async context manager."
            )

        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        logger.debug("DeepInfra request model=%s prompt_len=%d", self._model, len(prompt))

        response = await self._http.post("/chat/completions", content=json.dumps(payload))

        if response.status_code != 200:
            raise DeepInfraError(
                f"DeepInfra API error {response.status_code}: {response.text[:300]}"
            )

        data = response.json()
        content: str = data["choices"][0]["message"]["content"]

        logger.debug(
            "DeepInfra response model=%s finish_reason=%s",
            self._model,
            data["choices"][0].get("finish_reason"),
        )

        return content

    @property
    def model(self) -> str:
        return self._model