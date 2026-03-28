import json
from utils.logger import log_experiment_to_csv

def run_task_r2(model_func, model_name, iteration=1):
    # Wczytanie tego samego opisu systemu z JSON
    with open('inputs/descriptions_r2.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    system_description = data['reservations']
    
    # Prompty specyficzne dla R2 (User Stories i Acceptance Criteria)
    system_prompt = "Jesteś analitykiem wymagań. Twoim zadaniem jest przekształcenie surowego opisu systemu w ustrukturyzowane wymagania."
    user_prompt = f"Opis systemu: {system_description}\n\nNa podstawie powyższego opisu utwórz kompletne User Stories. Do każdego User Story dopisz szczegółowe kryteria akceptacji (Acceptance Criteria) używając formatu Given-When-Then."

    print(f"[Zadanie R2] Odpytuję model {model_name}...")
    llm_response = model_func(system_prompt, user_prompt, temperature=0.2)
    
    print("\n=== ODPOWIEDŹ MODELU ===")
    print(llm_response)
    print("========================\n")
    
    log_experiment_to_csv("r2-refinement.csv", "R2", model_name, "LLM-only", iteration, user_prompt, llm_response)
    print(f"-> Zapisano wyniki R2 dla modelu {model_name}")