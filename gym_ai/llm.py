"""
LLM abstraction layer supporting sync and async generation, streaming,
JSON mode, and Qwen <think> token filtering via DashScope/OpenAI.
"""

import logging
import re
import sys
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional

from openai import AsyncOpenAI, OpenAI

from gym_ai.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT

logger = logging.getLogger("gym_ai.llm")

effective_key = (LLM_API_KEY or "").strip() or "sk-placeholder-key-not-set"

# Synchronous and Asynchronous clients
sync_client = OpenAI(
    api_key=effective_key,
    base_url=LLM_BASE_URL,
    timeout=LLM_TIMEOUT,
)

async_client = AsyncOpenAI(
    api_key=effective_key,
    base_url=LLM_BASE_URL,
    timeout=LLM_TIMEOUT,
)


def strip_thinking_tokens(text: str) -> str:
    """Remove <think>...</think> reasoning blocks from Qwen model output."""
    if not text:
        return ""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _format_messages(
    prompt: str,
    system_prompt: Optional[str] = None,
    chat_history: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, str]]:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt.strip()})

    if chat_history:
        for msg in chat_history:
            if isinstance(msg, dict) and msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({
                    "role": str(msg["role"]),
                    "content": str(msg["content"]),
                })

    messages.append({"role": "user", "content": prompt})
    return messages


def generate_answer(
    prompt: str,
    system_prompt: Optional[str] = None,
    chat_history: Optional[List[Dict[str, Any]]] = None,
    stream: bool = False,
    json_mode: bool = False,
) -> Any:
    """
    Generate an answer synchronously using the configured Qwen model.
    When stream=True, returns a generator of text chunks.
    """
    try:
        messages = _format_messages(prompt, system_prompt, chat_history)
        kwargs: Dict[str, Any] = {
            "model": LLM_MODEL,
            "messages": messages,
            "temperature": 0.0,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        if stream:
            kwargs["stream"] = True
            response_stream = sync_client.chat.completions.create(**kwargs)

            def stream_generator() -> Generator[str, None, None]:
                buffer = ""
                inside_think = False
                for chunk in response_stream:
                    try:
                        delta = chunk.choices[0].delta
                        text = delta.content if delta and delta.content else ""
                        if not text:
                            continue

                        buffer += text
                        if inside_think:
                            if "</think>" in buffer:
                                _, _, after = buffer.partition("</think>")
                                buffer = ""
                                inside_think = False
                                if after:
                                    yield after
                        elif "<think>" in buffer:
                            before, _, remainder = buffer.partition("<think>")
                            if before:
                                yield before
                            buffer = remainder
                            inside_think = True
                        else:
                            yield buffer
                            buffer = ""
                    except Exception:
                        pass

                if buffer and not inside_think:
                    yield buffer

            return stream_generator()

        response = sync_client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        if content is not None:
            return strip_thinking_tokens(content)

        raise RuntimeError(f"Invalid response structure from LLM: {response}")

    except Exception as exc:
        logger.error(f"[Gym AI] LLM sync error: {exc}", exc_info=True)
        if stream:
            def error_generator():
                yield "I'm sorry, I couldn't generate a reply right now. Please try again in a moment."
            return error_generator()
        raise RuntimeError(f"LLM generation failed: {exc}") from exc


async def agenerate_answer(
    prompt: str,
    system_prompt: Optional[str] = None,
    chat_history: Optional[List[Dict[str, Any]]] = None,
    stream: bool = False,
    json_mode: bool = False,
) -> Any:
    """
    Generate an answer asynchronously using AsyncOpenAI.
    When stream=True, returns an async generator of text chunks.
    """
    try:
        messages = _format_messages(prompt, system_prompt, chat_history)
        kwargs: Dict[str, Any] = {
            "model": LLM_MODEL,
            "messages": messages,
            "temperature": 0.0,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        if stream:
            kwargs["stream"] = True
            response_stream = await async_client.chat.completions.create(**kwargs)

            async def async_stream_generator() -> AsyncGenerator[str, None]:
                buffer = ""
                inside_think = False
                async for chunk in response_stream:
                    try:
                        delta = chunk.choices[0].delta
                        text = delta.content if delta and delta.content else ""
                        if not text:
                            continue

                        buffer += text
                        if inside_think:
                            if "</think>" in buffer:
                                _, _, after = buffer.partition("</think>")
                                buffer = ""
                                inside_think = False
                                if after:
                                    yield after
                        elif "<think>" in buffer:
                            before, _, remainder = buffer.partition("<think>")
                            if before:
                                yield before
                            buffer = remainder
                            inside_think = True
                        else:
                            yield buffer
                            buffer = ""
                    except Exception:
                        pass

                if buffer and not inside_think:
                    yield buffer

            return async_stream_generator()

        response = await async_client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        if content is not None:
            return strip_thinking_tokens(content)

        raise RuntimeError(f"Invalid async response structure from LLM: {response}")

    except Exception as exc:
        logger.error(f"[Gym AI] LLM async error: {exc}", exc_info=True)
        if stream:
            async def async_error_generator():
                yield "I'm sorry, I couldn't generate a reply right now. Please try again in a moment."
            return async_error_generator()
        raise RuntimeError(f"Async LLM generation failed: {exc}") from exc


import os

VISION_MODEL = os.getenv("VISION_MODEL", "qwen-vl-max")


def generate_vision_analysis(
    prompt: str,
    image_url_or_b64: str,
    system_prompt: Optional[str] = None,
    json_mode: bool = True,
) -> str:
    """
    Generate multimodal analysis using Qwen-VL.
    Accepts raw base64, data-URI base64, or remote image URL.
    """
    if not image_url_or_b64.startswith("http") and not image_url_or_b64.startswith("data:"):
        image_url = f"data:image/jpeg;base64,{image_url_or_b64}"
    else:
        image_url = image_url_or_b64

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt.strip()})

    messages.append({
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_url}},
        ],
    })

    kwargs = {
        "model": VISION_MODEL,
        "messages": messages,
        "temperature": 0.2,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        response = sync_client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        return strip_thinking_tokens(content)
    except Exception as exc:
        logger.error(f"[Gym AI] Vision analysis error: {exc}", exc_info=True)
        raise RuntimeError(f"Vision analysis failed: {exc}") from exc


async def agenerate_vision_analysis(
    prompt: str,
    image_url_or_b64: str,
    system_prompt: Optional[str] = None,
    json_mode: bool = True,
) -> str:
    """
    Asynchronous multimodal analysis using Qwen-VL.
    """
    if not image_url_or_b64.startswith("http") and not image_url_or_b64.startswith("data:"):
        image_url = f"data:image/jpeg;base64,{image_url_or_b64}"
    else:
        image_url = image_url_or_b64

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt.strip()})

    messages.append({
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_url}},
        ],
    })

    kwargs = {
        "model": VISION_MODEL,
        "messages": messages,
        "temperature": 0.2,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        response = await async_client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        return strip_thinking_tokens(content)
    except Exception as exc:
        logger.error(f"[Gym AI] Async vision analysis error: {exc}", exc_info=True)
        raise RuntimeError(f"Async vision analysis failed: {exc}") from exc

