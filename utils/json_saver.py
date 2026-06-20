import json, os

from utils.paths import get_output_dir

def save_artifact(data: dict, filename: str, output_dir: str | None = None):
    resolved_output_dir = output_dir or get_output_dir()
    os.makedirs(resolved_output_dir, exist_ok=True)
    path = os.path.join(resolved_output_dir, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)