"""Shared Anthropic Claude client with retry, rate limiting, and JSON parsing."""

import asyncio
import json
import logging
import time
from typing import Type, TypeVar

import anthropic
from pydantic import BaseModel

from config.settings import settings

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class ClaudeClient:
    """Async-safe Claude client wrapping the synchronous Anthropic SDK."""

    def __init__(self):
        if not settings.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. Please set it in your .env file."
            )
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
        self._loop = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        return asyncio.get_event_loop()

    def _sync_generate(self, prompt: str, system: str, max_tokens: int) -> str:
        """Synchronous call to Anthropic API (runs in executor)."""
        messages = [{"role": "user", "content": prompt}]
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 2048,
    ) -> str:
        """Generate text from Claude with retry and exponential backoff."""
        async with self._semaphore:
            last_error = None
            for attempt in range(settings.max_retries):
                try:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, self._sync_generate, prompt, system, max_tokens
                    )
                    return result
                except anthropic.RateLimitError as e:
                    wait = settings.base_retry_delay * (2**attempt)
                    logger.warning(
                        f"Rate limit hit (attempt {attempt + 1}/{settings.max_retries}). "
                        f"Waiting {wait:.1f}s..."
                    )
                    last_error = e
                    await asyncio.sleep(wait)
                except anthropic.APIStatusError as e:
                    if e.status_code >= 500:
                        wait = settings.base_retry_delay * (2**attempt)
                        logger.warning(
                            f"Server error {e.status_code} (attempt {attempt + 1}). "
                            f"Waiting {wait:.1f}s..."
                        )
                        last_error = e
                        await asyncio.sleep(wait)
                    else:
                        logger.error(f"Non-retryable API error {e.status_code}: {e}")
                        raise
                except anthropic.APIError as e:
                    wait = settings.base_retry_delay * (2**attempt)
                    logger.warning(
                        f"API error (attempt {attempt + 1}/{settings.max_retries}): {e}. "
                        f"Waiting {wait:.1f}s..."
                    )
                    last_error = e
                    await asyncio.sleep(wait)
                except Exception as e:
                    logger.error(f"Unexpected error calling Claude: {e}")
                    raise

            raise RuntimeError(
                f"Claude API failed after {settings.max_retries} retries. "
                f"Last error: {last_error}"
            )

    async def generate_json(
        self,
        prompt: str,
        system: str,
        schema_class: Type[T],
        max_tokens: int = 2048,
    ) -> T:
        """Generate and parse a JSON response as a Pydantic model."""
        json_system = (
            f"{system}\n\nIMPORTANT: Respond ONLY with valid JSON. "
            "Do not include markdown code fences, explanations, or any text outside the JSON."
        )

        for parse_attempt in range(3):
            raw = await self.generate(prompt, json_system, max_tokens)

            # Strip markdown code fences if present
            text = raw.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                # Remove first and last fence lines
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            text = text.strip()

            try:
                data = json.loads(text)
                return schema_class.model_validate(data)
            except json.JSONDecodeError as e:
                logger.warning(
                    f"JSON parse error on attempt {parse_attempt + 1}: {e}. "
                    f"Raw response (first 500 chars): {raw[:500]}"
                )
                if parse_attempt < 2:
                    # Retry with a cleaner prompt
                    prompt = (
                        f"{prompt}\n\n"
                        "Previous response had a JSON parse error. "
                        "Return ONLY a raw JSON object, no markdown, no explanation."
                    )
                    await asyncio.sleep(1.0)
            except Exception as e:
                logger.warning(
                    f"Pydantic validation error on attempt {parse_attempt + 1}: {e}"
                )
                raise

        raise ValueError(
            f"Failed to parse valid JSON response after 3 attempts. "
            f"Last raw response: {raw[:500]}"
        )

    async def generate_json_list(
        self,
        prompt: str,
        system: str,
        max_tokens: int = 4096,
    ) -> list:
        """Generate and parse a JSON array response."""
        json_system = (
            f"{system}\n\nIMPORTANT: Respond ONLY with a valid JSON array. "
            "Do not include markdown code fences, explanations, or any text outside the JSON array."
        )

        for parse_attempt in range(3):
            raw = await self.generate(prompt, json_system, max_tokens)

            text = raw.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            text = text.strip()

            try:
                data = json.loads(text)
                if not isinstance(data, list):
                    logger.warning(f"Expected JSON array but got {type(data).__name__}")
                    data = [data] if isinstance(data, dict) else []
                return data
            except json.JSONDecodeError as e:
                logger.warning(
                    f"JSON list parse error on attempt {parse_attempt + 1}: {e}. "
                    f"Raw (first 500 chars): {raw[:500]}"
                )
                if parse_attempt < 2:
                    prompt = (
                        f"{prompt}\n\n"
                        "Previous response had a JSON parse error. "
                        "Return ONLY a raw JSON array [...], no markdown, no explanation."
                    )
                    await asyncio.sleep(1.0)

        logger.error("Failed to get valid JSON list after 3 attempts, returning empty list")
        return []
