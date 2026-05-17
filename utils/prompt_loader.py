from __future__ import annotations

from pathlib import Path
from string import Template
from typing import Any


def load_prompt(path: str | Path) -> str:
    prompt_path = Path(path)
    return prompt_path.read_text(encoding="utf-8")


def render_prompt(path: str | Path, **kwargs: Any) -> str:
    template = Template(load_prompt(path))
    return template.safe_substitute(**kwargs)
