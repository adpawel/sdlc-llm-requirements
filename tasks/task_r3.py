import json
from utils.logger import log_experiment_to_csv


def run_task_r2_generate_whole_artifact(model_func, model_name, case_study, iteration=1):
    with open('inputs/descriptions_r3.json', 'r', encoding='utf-8') as f:
        system_description = json.load(f)[case_study]

    system_prompt = """Jesteś Doświadczonym Analitykiem Wymagań (Senior Business Analyst). TTwoją specjalnością jest krytyczna weryfikacja surowych koncepcji biznesowych.
        Twoim zadaniem jest dogłębna analiza dostarczonego opisu systemu pod kątem wykrywania konfliktów (sytuacji, w których reguła A wyklucza regułę B lub proces nie może zostać ukończony z powodu sprzecznych założeń).
        Rozwiązując konflikty, operuj wyłącznie w ramach dostarczonego kontekstu. Nie dodawaj nowych, niewymienionych wcześniej modułów ani funkcjonalności."""

    user_prompt = f"""Przeanalizuj poniższy surowy opis systemu:

        <opis>
        {system_description}
        </opis>

        Zwróć wynik w formacie Markdown, zachowując dokładnie dwie poniższe sekcje:

        ### 1. Lista wykrytych konfliktów
        Wypunktuj wszystkie znalezione konflikty w dostarczonym opisie. Przy każdym punkcie krótko (jedno zdanie) uzasadnij, na czym polega problem.

        ### 2. Poprawiona wersja
        Sformułuj nowy, spójny opis systemu w formie tekstu ciągłego, z którego usunięto wyżej wymienione konflikty, zachowując przy tym pierwotny cel biznesowy.

        WYMAGANIA FORMATOWANIA (OBOWIĄZKOWE):

        - W sekcji 1 każdy punkt MUSI zaczynać się od "- " (myślnik + spacja).
        - W sekcji 1 NIE używaj numeracji (1., 2., itd.) ani innych symboli list (np. *, •).
        - Sekcja 2 MUSI być tekstem ciągłym. NIE używaj w niej żadnych wypunktowań.
        - Nie dodawaj żadnego tekstu wprowadzającego, podsumowań ani komentarzy poza dwiema wymaganymi sekcjami."""

    print(f"[Zadanie R3] Odpytuję model {model_name}...")
    llm_response = model_func(system_prompt, user_prompt, temperature=0.2)
    
    print("\n=== ODPOWIEDŹ MODELU ===")
    print(llm_response)
    print("========================\n")
    
    log_experiment_to_csv("r3-conflict_detection.csv", "R3", model_name, "LLM-only", iteration, user_prompt, llm_response)
    print(f"-> Zapisano wyniki R3 dla modelu {model_name}")