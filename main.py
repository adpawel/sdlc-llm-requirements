import argparse

from models.llama_handler import get_llama_response
from models.openai_handler import get_openai_response
from models.claude_handler import get_claude_response
from models.gemini_handler import get_gemini_response
from tasks.task_r1 import run_task_r1
from tasks.task_r2_generate_whole_artifact import run_task_r2_generate_whole_artifact

def main(model_req, task_req, case_study):
    print("Starting test session SDLC-LLM Benchmark...")
    
    model_req = model_req.strip().lower()
    task_req = task_req.strip().lower()
    case_study = case_study.strip().lower()

    models = {
        "gemini" : (get_gemini_response, "gemini-3-flash-preview"),
        "claude" : (get_claude_response, "claude-sonnet-4-6"),
        "gpt" : (get_openai_response, "gpt-5.4"),
        "llama" : (get_llama_response, "llama-3.1:8b")
    }
    
    tasks = {
        "r1" : run_task_r1,
        "r2" : run_task_r2_generate_whole_artifact
    }

    if model_req not in models:
        raise ValueError(f"We dont have access to: {model_req} model.")
    
    if task_req not in tasks:
        raise ValueError(f"We have only {len(tasks)} tasks - {list(tasks.keys())}")

    current_model_func, current_model_name = models[model_req] 
    task_fun = tasks[task_req]
    
    try:
        task_fun(current_model_func, current_model_name, case_study)
        
    except Exception as e:
        print(f"Error occured: {e}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SDLC-LLM Benchmark Runner",
        epilog="Przykład użycia: uv run .\\main.py gemini r1 appointment-booking"
    )
    
    parser.add_argument(
        "model", 
        type=str,
        choices=["gemini", "claude", "llama", "gpt"],
        help="Choose LLM models"
    )
    parser.add_argument(
        "task", 
        type=str, 
        choices=["r1", "r2", "r3"],
        help="Choose task number"
    )
    parser.add_argument(
        "case_study", 
        type=str, 
        choices=["appointment-booking", "helpdesk-ticketing", "file-storage-api"],
        help="Choose case study."
    )
    
    # Odczytanie argumentów wpisanych w konsoli
    args = parser.parse_args()

    main(args.model, args.task, args.case_study)