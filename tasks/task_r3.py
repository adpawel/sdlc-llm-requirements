import json
from pathlib import Path
import time

from utils.logger import log_experiment_to_csv
from utils.paths import get_prompt_dir
from utils.prompt_loader import render_prompt


def run_task_r3(model_func, model_name, case_study, iteration=1):
    with open('inputs/descriptions_r3_gold_ver2.json', 'r', encoding='utf-8') as f:
        system_description = json.load(f)[case_study]

    prompt_dir = Path(get_prompt_dir()) / "r3"

    system_prompt = render_prompt(prompt_dir / "system.txt")
    user_prompt = render_prompt(
        prompt_dir / "user.txt",
        system_description=system_description,
    )

    print(f"[Zadanie R3] Odpytuję model {model_name}...")
    start = time.time()
    llm_response = model_func(system_prompt, user_prompt, temperature=0.2)
    elapsed = round(time.time() - start, 2)
    
    print("\n=== ODPOWIEDŹ MODELU ===")
    print(llm_response)
    print("========================\n")
    
    log_experiment_to_csv("r3-conflict_detection_gold_ver2.csv", "R3", model_name, "LLM-only", iteration, user_prompt, llm_response, elapsed)
    print(f"-> Zapisano wyniki R3 dla modelu {model_name} (czas: {elapsed}s)")