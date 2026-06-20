from __future__ import annotations

import json
import os

from orchestrator import run_multi_stakeholder_experiment
from utils.model_registry import resolve_model


def run_task_multi_stakeholder(model_func, model_name, case_study, iteration=1):
    with open("inputs/descriptions_r2_gold_ver2.json", "r", encoding="utf-8") as f:
        system_description = json.load(f)[case_study]

    evaluator_model_key = os.getenv("SDLC_EVALUATOR_MODEL", "").strip()
    evaluator_model_func = model_func
    evaluator_model_name = model_name
    if evaluator_model_key:
        evaluator_model_func, evaluator_model_name = resolve_model(evaluator_model_key)

    return run_multi_stakeholder_experiment(
        model_func=model_func,
        model_name=model_name,
        evaluator_model_func=evaluator_model_func,
        evaluator_model_name=evaluator_model_name,
        case_study=case_study,
        system_description=system_description,
        iteration=iteration,
    )
