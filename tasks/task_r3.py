import json
from utils.logger import log_experiment_to_csv

def run_task_r3(model_func, model_name, iteration=1):
    # Wczytanie tego samego opisu systemu z JSON
    with open('inputs/descriptions_r3.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # TODO