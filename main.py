import os
import csv
from models.openai_handler import get_openai_response
from models.claude_handler import get_claude_response
from models.gemini_handler import get_gemini_response
from models.llama_handler import get_llama_response

def log_experiment_to_csv(task_id, model_name, mode, iteration, prompt, output):
    """
    Centralna funkcja do zapisu logów z zachowaniem ujednoliconego formatu.
    Zapisuje wyniki do folderu 'outputs/'.
    """
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    
    csv_filename = os.path.join(output_dir, "r1-inconsistencies.csv")
    
    file_exists = os.path.isfile(csv_filename)
    
    with open(csv_filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        if not file_exists:
            writer.writerow([
                "ID_Zadania", "Model", "Tryb", "Iteracja", 
                "Wejscie_Prompt", "Odpowiedz_LLM", 
                "Ocena_Merytoryczna_1", "Ocena_Merytoryczna_2", "Ocena_Merytoryczna_3"
            ])
            
        writer.writerow([task_id, model_name, mode, iteration, prompt, output, "", "", ""])
        

def main():
    system_description = "System umożliwia rezerwację wizyt. Użytkownicy mogą anulować wizyty i zarządzać nimi."
    system_prompt = "Jesteś analitykiem wymagań. Twoim zadaniem jest analiza opisu systemu pod kątem wykrycia wszelkich niejednoznaczności, braków oraz konfliktów logicznych."
    user_prompt = f"Opis systemu: {system_description}\n\nWypisz wszystkie niejednoznaczności i braki. Sformułuj konkretne pytania do interesariuszy. Zwróć wynik jako wypunktowaną listę."

    print("Wysyłam zapytanie...")
    
    try:
        # llm_response = get_openai_response(system_prompt, user_prompt, temperature=0.2)
        # model_name = "gpt-4o"
        # llm_response = get_claude_response(system_prompt, user_prompt, temperature=0.2)
        # model_name = "claude-3-5-sonnet"
        # llm_response = get_gemini_response(system_prompt, user_prompt, temperature=0.2)
        # model_name = "gemini-3-flash"
        llm_response = get_llama_response(system_prompt, user_prompt, temperature=0.2)
        model_name = "llama-3.1"
        
        print("\n=== ODPOWIEDŹ MODELU ===")
        print(llm_response)
        print("========================\n")
        
        log_experiment_to_csv(
            task_id="R1", 
            model_name=model_name, 
            mode="LLM-only", 
            iteration=1,
            prompt=user_prompt, 
            output=llm_response
        )
        print("-> Pomyślnie zapisano logi do pliku .csv")
        
    except Exception as e:
        print(f"Wystąpił błąd podczas komunikacji z API: {e}")

if __name__ == "__main__":
    main()