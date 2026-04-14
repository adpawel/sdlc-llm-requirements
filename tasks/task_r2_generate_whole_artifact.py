import json
from schemas.requirements_artifact import RequirementsArtifact
from utils.logger import log_experiment_to_csv
from utils.json_saver import save_artifact
from pydantic import ValidationError
import time

def run_task_r2_generate_whole_artifact(model_func, model_name, case_study, iteration=1):
    with open('inputs/descriptions_r2.json', 'r', encoding='utf-8') as f:
        system_description = json.load(f)[case_study]

    system_prompt = """Jesteś analitykiem wymagań. Odpowiadaj WYŁĄCZNIE poprawnym JSON.
Żadnego Markdown ani komentarzy."""

    # Krok 1 – role + FR
    user_prompt_1 = f"""Opis systemu: {system_description}

Wygeneruj TYLKO ten fragment JSON z dokładnie taką strukturą:
{{
  "roles": [
    {{"name": "NazwaRoli", "permissions": ["uprawnienie1", "uprawnienie2"]}}
  ],
  "functional_requirements": [
    {{"id": "FR1", "description": "Treść wymagania."}}
  ]
}}"""

    r1, raw_response_1, time_1 = _call_and_parse(model_func, model_name, system_prompt, user_prompt_1, step=1)
    log_experiment_to_csv("r2-results.csv", "R2-krok1", model_name, "LLM-only", iteration, user_prompt_1, raw_response_1, time_1)

    # Krok 2 – NFR + user stories
    user_prompt_2 = f"""Opis systemu: {system_description}
Wygenerowane FR: {json.dumps(r1, ensure_ascii=False)}

Wygeneruj TYLKO ten fragment JSON z dokładnie taką strukturą:
{{
  "non_functional_requirements": [
    {{"id": "NFR1", "description": "Treść wymagania."}}
  ],
  "user_stories": [
    {{"id": "US1", "description": "Jako X chcę Y, aby Z."}}
  ]
}}"""

    r2, raw_response_2, time_2 = _call_and_parse(model_func, model_name, system_prompt, user_prompt_2, step=2)
    log_experiment_to_csv("r2-results.csv", "R2-krok2", model_name, "LLM-only", iteration, user_prompt_2, raw_response_2, time_2)

    # Krok 3 – AC
    user_prompt_3 = f"""User stories: {json.dumps(r2.get('user_stories', []), ensure_ascii=False)}

Wygeneruj TYLKO ten fragment JSON z dokładnie taką strukturą:
{{
  "acceptance_criteria": [
    {{
      "id": "AC1",
      "given": "warunek wstępny",
      "when": "akcja użytkownika",
      "then": "oczekiwany rezultat"
    }}
  ]
}}"""

    r3, raw_response_3, time_3 = _call_and_parse(model_func, model_name, system_prompt, user_prompt_3, step=3)
    log_experiment_to_csv("r2-results.csv", "R2-krok3", model_name, "LLM-only", iteration, user_prompt_3, raw_response_3, time_3)

    # Złożenie całości
    prompt_log = f"[SYSTEM]\n{system_prompt}\n\n[KROK1]\n{user_prompt_1}\n\n[KROK2]\n{user_prompt_2}\n\n[KROK3]\n{user_prompt_3}"

    raw = {
        "system_goal": system_description[:200],
        **r1, **r2, **r3,
        "metadata": {
            "version": "llm",
            "case_study": case_study,
            "model_used": model_name,
            "prompt_log": prompt_log
        }
    }

    artifact = None
    try:
        artifact = RequirementsArtifact.model_validate(raw)
        save_artifact(artifact.model_dump(), f"artifact_r2_{model_name.split("-")[0]}_{case_study}.json")
        print("-> Walidacja OK")
    except ValidationError as e:
        print(f"[ERROR] Walidacja Pydantic:\n{e}")

    return artifact


def _call_and_parse(model_func, model_name, system_prompt, user_prompt, step: int) -> tuple[dict, str, float]:
    for attempt in range(3):
        start = time.time()
        response = model_func(system_prompt, user_prompt, temperature=0.2)
        elapsed = round(time.time() - start, 2)
        try:
            return json.loads(response), response, elapsed
        except json.JSONDecodeError:
            try:
                import ast
                fixed = ast.literal_eval(response)
                return fixed, response, elapsed
            except Exception:
                print(f"[WARN] Krok {step}, próba {attempt+1}: błędny JSON, retry...")
                print(f"[DEBUG] Surowa odpowiedź:\n{response}\n")
    print(f"[ERROR] Krok {step}: nie udało się po 3 próbach")
    return {}, "", 0.0