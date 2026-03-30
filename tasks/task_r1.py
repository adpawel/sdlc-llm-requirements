import json
from utils.logger import log_experiment_to_csv

def run_task_r1(model_func, model_name, iteration=1):
    # Wczytanie opisu systemu z JSON
    with open('inputs/descriptions_r1.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    system_description = data['file_storage']
    
    # Prompty specyficzne dla R1
    system_prompt = """Jesteś Doświadczonym Analitykiem Wymagań (Senior Business Analyst). Twoją specjalnością jest krytyczna weryfikacja surowych koncepcji biznesowych. 
Twoim zadaniem jest dogłębna analiza dostarczonego opisu systemu pod kątem wykrywania niejednoznaczności, brakujących informacji oraz konfliktów logicznych. 
Zasady:
1. Skup się na przypadkach brzegowych (edge cases), logice biznesowej, bezpieczeństwie i przepływie danych.
2. Skup się na jakości, a nie ilości. Nie wymyślaj trywialnych problemów (np. UI/UX).
3. Nie wymyślaj nowych funkcjonalności - analizuj tylko to, co wynika z tekstu (lub czego w nim ewidentnie brakuje).
4. Bądź precyzyjny i dociekliwy."""

    user_prompt = f"""Przeanalizuj poniższy surowy opis systemu:

<opis>
{system_description}
</opis>

Zwróć wynik w formacie Markdown, zachowując dokładnie dwie poniższe sekcje:

### 1. Lista problemów
Wypunktuj najważniejsze niejednoznaczności, braki informacji oraz konflikty logiczne w dostarczonym opisie. Przy każdym punkcie krótko (jedno zdanie) uzasadnij, na czym polega problem.

### 2. Pytania do doprecyzowania
Sformułuj listę konkretnych pytań do interesariuszy, które pozwolą rozwiązać wyżej wymienione problemy. Tam gdzie to możliwe, zaproponuj w pytaniu warianty do wyboru, aby ułatwić podjęcie decyzji biznesowej.

WYMAGANIA FORMATOWANIA (OBOWIĄZKOWE):

Każdy punkt w obu sekcjach MUSI zaczynać się od "- " (myślnik + spacja)
NIE używaj numeracji (1., 2., itd.)
NIE używaj innych symboli list (np. *, •)
Każdy punkt w osobnej linii
Nie dodawaj żadnych dodatkowych sekcji ani komentarzy"""

    print(f"[Zadanie R1] Odpytuję model {model_name}...")
    llm_response = model_func(system_prompt, user_prompt, temperature=0.2)
    
    print("\n=== ODPOWIEDŹ MODELU ===")
    print(llm_response)
    print("========================\n")
    
    log_experiment_to_csv("r1-inconsistencies.csv", "R1", model_name, "LLM-only", iteration, user_prompt, llm_response)
    print(f"-> Zapisano wyniki R1 dla modelu {model_name}")