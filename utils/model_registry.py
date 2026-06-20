from __future__ import annotations

from typing import Callable

from models.llama_handler import get_llama_response
from models.openai_handler import get_openai_response
from models.claude_handler import get_claude_response
from models.gemini_handler import get_gemini_response


MODEL_REGISTRY: dict[str, tuple[Callable[[str, str, float], str], str]] = {
    "gemini": (get_gemini_response, "gemini-3-flash-preview"),
    "claude": (get_claude_response, "claude-sonnet-4-6"),
    "gpt": (get_openai_response, "gpt-5.4"),
    "llama": (get_llama_response, "llama-3.1-8b"),
}


def resolve_model(model_key: str) -> tuple[Callable[[str, str, float], str], str]:
    key = model_key.strip().lower()
    if key not in MODEL_REGISTRY:
        raise ValueError(f"Unknown model key: {model_key}")
    return MODEL_REGISTRY[key]
