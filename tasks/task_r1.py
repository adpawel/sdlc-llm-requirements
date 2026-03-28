import json
from utils.logger import log_experiment_to_csv

def run_task_r1(model_func, model_name, iteration=1):
    # Wczytanie opisu systemu z JSON
    with open('inputs/descriptions_r1.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    system_description = data['reservations']
    
    # Prompty specyficzne dla R1
    system_prompt = "Jesteś analitykiem wymagań. Twoim zadaniem jest analiza opisu systemu pod kątem wykrycia wszelkich niejednoznaczności, braków oraz konfliktów logicznych."
    user_prompt = f"Opis systemu: {system_description}\n\nWypisz wszystkie niejednoznaczności i braki. Sformułuj konkretne pytania do interesariuszy. Zwróć wynik jako wypunktowaną listę."

    print(f"[Zadanie R1] Odpytuję model {model_name}...")
    llm_response = model_func(system_prompt, user_prompt, temperature=0.2)
    
    print("\n=== ODPOWIEDŹ MODELU ===")
    print(llm_response)
    print("========================\n")
    
    log_experiment_to_csv("r1-inconsistencies.csv", "R1", model_name, "LLM-only", iteration, user_prompt, llm_response)
    print(f"-> Zapisano wyniki R1 dla modelu {model_name}")