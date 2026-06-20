from __future__ import annotations

from pathlib import Path
import os

DEFAULT_EXPERIMENT = "llm_only"


def get_experiment_name() -> str:
    name = os.getenv("SDLC_EXPERIMENT", DEFAULT_EXPERIMENT).strip()
    return name or DEFAULT_EXPERIMENT


def get_output_dir() -> str:
    experiment = get_experiment_name()
    variant = os.getenv("SDLC_EXPERIMENT_VARIANT", "").strip()
    if experiment == "multi_stakeholder":
        variant = variant or "no_weights_zero_temp"
        return str(Path("outputs") / experiment / variant)
    return str(Path("outputs") / experiment)


def get_prompt_dir() -> str:
    return str(Path("prompts") / get_experiment_name())
