from models.llama_handler import get_llama_response
from models.openai_handler import get_openai_response
from models.claude_handler import get_claude_response
from models.gemini_handler import get_gemini_response
from tasks.task_r1 import run_task_r1
from tasks.task_r2 import run_task_r2

def main():
    print("Rozpoczynam sesję testową SDLC-LLM Benchmark...")
    
    # current_model_func = get_openai_response
    # current_model_name = "gpt-5.4"
    current_model_func = get_claude_response
    current_model_name = "claude-sonnet-4-6"
    # current_model_func = get_gemini_response
    # current_model_name = "gemini-3-flash-preview"
    # current_model_func = get_llama_response
    # current_model_name = "llama-3.1:8b"
    
    try:
        # Test zadania R1
        run_task_r1(current_model_func, current_model_name, iteration=1)
        
        # Test zadania R2
        # run_task_r2(current_model_func, current_model_name)
        
    except Exception as e:
        print(f"Wystąpił błąd: {e}")

if __name__ == "__main__":
    main()