import os
import csv

def log_experiment_to_csv(filename, task_id, model_name, mode, iteration, prompt, output):
    """
    Centralna funkcja do zapisu logów z zachowaniem ujednoliconego formatu.
    """
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    
    csv_filename = os.path.join(output_dir, filename)
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