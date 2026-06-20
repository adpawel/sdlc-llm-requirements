import json
from pathlib import Path

from utils.logger import log_experiment_to_csv
from utils.paths import get_prompt_dir
from utils.prompt_loader import render_prompt

def run_task_r1(model_func, model_name, case_study, iteration=1):
    # Wczytanie opisu systemu z JSON
    with open('inputs/descriptions_r1.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    system_description = data[case_study]
    
    prompt_dir = Path(get_prompt_dir()) / "r1"

    system_prompt = render_prompt(prompt_dir / "system.txt")
    user_prompt = render_prompt(
        prompt_dir / "user.txt",
        system_description=system_description,
    )

    print(f"[Zadanie R1] Odpytuję model {model_name}...")
    llm_response = model_func(system_prompt, user_prompt, temperature=0.2)
    
    print("\n=== ODPOWIEDŹ MODELU ===")
    print(llm_response)
    print("========================\n")
    
    log_experiment_to_csv("r1-inconsistencies.csv", "R1", model_name, "LLM-only", iteration, user_prompt, llm_response)
    print(f"-> Zapisano wyniki R1 dla modelu {model_name}")