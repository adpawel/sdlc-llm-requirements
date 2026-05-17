from __future__ import annotations

import json

from orchestrator import run_multi_stakeholder_experiment


def run_task_multi_stakeholder(model_func, model_name, case_study, iteration=1):
    with open("inputs/descriptions_r2_gold_ver2.json", "r", encoding="utf-8") as f:
        system_description = json.load(f)[case_study]

    return run_multi_stakeholder_experiment(
        model_func=model_func,
        model_name=model_name,
        case_study=case_study,
        system_description=system_description,
        iteration=iteration,
    )
