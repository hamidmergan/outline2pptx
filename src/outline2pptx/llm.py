"""Calls to an OpenAI-compatible server: one chat call whose answer should be JSON, and one image call."""

from __future__ import annotations

import base64
import logging
import re

from .config import Settings
from .errors import ModelError

log = logging.getLogger(__name__)

# Probed once per process instead of again on every call.
_json_mode_supported = True
_THINK = re.compile(r"<think>.*?</think>", re.S)
TEMPERATURE = 0.4


def make_client(settings: Settings):
    from openai import OpenAI

    return OpenAI(
        base_url=settings.base_url,
        api_key=settings.api_key,
        timeout=settings.timeout,
        max_retries=settings.max_retries,
    )


def make_image_client(settings: Settings):
    from openai import OpenAI

    if not settings.has_image_model:
        raise ModelError("No image model is set.")
    return OpenAI(
        base_url=settings.image_base_url,
        api_key=settings.image_api_key,
        timeout=settings.image_timeout,
        max_retries=settings.max_retries,
    )


def _rejects_json_mode(exc: Exception) -> bool:
    """True when the provider explicitly rejected response_format."""
    if getattr(exc, "status_code", None) != 400:
        return False
    text = str(exc).lower()
    return "response_format" in text or "json" in text


def _create(client, settings: Settings, messages: list[dict], *, json_mode: bool) -> str:
    kwargs: dict = {"temperature": TEMPERATURE}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(model=settings.model, messages=messages, **kwargs)
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, TypeError):
        raise ModelError("The server response has an unexpected format.")
    return _THINK.sub("", content or "")


def call_json(client, settings: Settings, messages: list[dict]) -> str:
    """One run, in JSON mode where the provider can do it."""
    global _json_mode_supported
    if _json_mode_supported:
        try:
            return _create(client, settings, messages, json_mode=True)
        except Exception as exc:
            if not _rejects_json_mode(exc):
                raise ModelError(f"Request to {settings.base_url} failed: {exc}") from exc
            log.warning("The provider refused JSON mode, this process asks without it from now on: %s", exc)
            _json_mode_supported = False
    try:
        return _create(client, settings, messages, json_mode=False)
    except ModelError:
        raise
    except Exception as exc:
        raise ModelError(f"Request to {settings.base_url} failed: {exc}") from exc


_FALLBACK_SIZE = "1024x1024"


def call_image(client, settings: Settings, prompt: str, size: str) -> bytes:
    """One picture as bytes, the square size as a fallback when the provider refuses ours."""
    answer = None
    for wanted in (size, _FALLBACK_SIZE):
        try:
            answer = client.images.generate(model=settings.image_model, prompt=prompt, size=wanted,
                                            n=1, response_format="b64_json")
            break
        except Exception as exc:
            if getattr(exc, "status_code", None) != 400 or wanted == _FALLBACK_SIZE:
                raise ModelError(f"Image provider: {exc}") from exc
    data = getattr(answer, "data", None) or []
    if not data:
        raise ModelError("No picture was generated.")
    entry = data[0]
    if getattr(entry, "b64_json", None):
        return base64.b64decode(entry.b64_json)
    url = getattr(entry, "url", None)
    if url:
        import httpx

        return httpx.get(url, timeout=settings.image_timeout).content
    raise ModelError("The answer holds no picture data.")
