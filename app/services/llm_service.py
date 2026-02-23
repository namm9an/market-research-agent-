"""LLM service — connects to vLLM's OpenAI-compatible API."""

import logging
import httpx
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from app.config import (
    MODEL_NAME,
    VLLM_BASE_URL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
)

logger = logging.getLogger(__name__)


async def check_vllm_health() -> bool:
    """Check if vLLM server is reachable."""
    try:
        base = VLLM_BASE_URL.rstrip("/").removesuffix("/v1")
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base}/health")
            return resp.status_code == 200
    except Exception as e:
        logger.warning(f"vLLM health check failed: {e}")
        return False


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True
)
async def chat_completion(
    messages: list[dict[str, str]],
    temperature: float = LLM_TEMPERATURE,
    max_tokens: int = LLM_MAX_TOKENS,
) -> str:
    """Send a chat completion request to vLLM and return the response text.

    Args:
        messages: List of message dicts with 'role' and 'content'.
        temperature: Override default temperature.
        max_tokens: Override default max tokens.

    Returns:
        The assistant's response text.

    Raises:
        httpx.HTTPStatusError: If vLLM returns an error.
        httpx.ConnectError: If vLLM is unreachable.
    """
    url = f"{VLLM_BASE_URL.rstrip('/')}/chat/completions"

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": temperature or LLM_TEMPERATURE,
        "max_tokens": max_tokens or LLM_MAX_TOKENS,
    }

    logger.info(f"LLM request: {len(messages)} messages, model={MODEL_NAME}")

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            logger.error(f"vLLM error {resp.status_code}: {resp.text[:500]}")
        resp.raise_for_status()

    data = resp.json()
    content = data["choices"][0]["message"]["content"]

    # Strip <think>...</think> reasoning tags if present (Nemotron reasoning mode)
    if "</think>" in content:
        content = content.split("</think>", 1)[-1].strip()

    logger.info(f"LLM response: {len(content)} chars")
    return content
