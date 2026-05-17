from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable
import time

from pydantic import ValidationError

from schemas.requirements_artifact import RequirementsArtifact
from utils.json_saver import save_artifact
from utils.logger import log_experiment_to_csv
from utils.paths import get_prompt_dir
from utils.prompt_loader import render_prompt


@dataclass(frozen=True)
class StakeholderRun:
    name: str
    goals: list[str]
    needs: list[str]
    concerns: list[str]
    priorities: list[str]
    constraints: list[str]
    tradeoffs: list[str]
    raw_response: str


@dataclass(frozen=True)
class OrchestrationResult:
    stakeholder_runs: list[StakeholderRun]
    requirements_artifact: dict
    traceability: dict
    stakeholder_evaluations: list[dict]


def run_multi_stakeholder_experiment(
    model_func,
    model_name: str,
    case_study: str,
    system_description: str,
    iteration: int = 1,
    stakeholder_agent_paths: Iterable[str] | None = None,
) -> OrchestrationResult:
    """Run the multi-stakeholder pipeline and return structured artifacts.

    This is a scaffold for the multi-stakeholder experiment and wires the
    stakeholder prompts, requirements synthesis, traceability, and evaluation.
    """
    prompt_root = Path(get_prompt_dir())
    agent_prompt_dir = prompt_root / "agents"
    engineer_prompt_dir = prompt_root / "requirements_engineer"
    traceability_prompt = prompt_root / "traceability" / "user.txt"
    evaluator_system_prompt = prompt_root / "evaluator" / "system.txt"
    evaluator_prompt = prompt_root / "evaluator" / "stakeholder_eval.txt"

    if not agent_prompt_dir.exists():
        raise FileNotFoundError(
            f"Missing prompts directory: {agent_prompt_dir}. "
            "Set SDLC_EXPERIMENT=multi_stakeholder before running."
        )

    agent_paths = list(stakeholder_agent_paths or _default_stakeholder_paths())
    stakeholder_runs: list[StakeholderRun] = []

    for agent_path in agent_paths:
        stakeholder_name = Path(agent_path).stem
        stakeholder_profile = Path(agent_path).read_text(encoding="utf-8")

        system_prompt = render_prompt(agent_prompt_dir / "system.txt")
        user_prompt = render_prompt(
            agent_prompt_dir / "user.txt",
            system_description=system_description,
            stakeholder_profile=stakeholder_profile,
            stakeholder_name=stakeholder_name,
        )

        stakeholder_payload, raw_response, elapsed = _call_and_parse(
            model_func,
            model_name,
            system_prompt,
            user_prompt,
            step=f"stakeholder-{stakeholder_name}",
        )
        log_experiment_to_csv(
            "r2-multi-stakeholder.csv",
            f"Stakeholder-{stakeholder_name}",
            model_name,
            "multi-stakeholder",
            iteration,
            user_prompt,
            raw_response,
            elapsed,
        )

        stakeholder_runs.append(
            StakeholderRun(
                name=stakeholder_name,
                goals=_coerce_list(stakeholder_payload.get("goals")),
                needs=_coerce_list(stakeholder_payload.get("needs")),
                concerns=_coerce_list(stakeholder_payload.get("concerns")),
                priorities=_coerce_list(stakeholder_payload.get("priorities")),
                constraints=_coerce_list(stakeholder_payload.get("constraints")),
                tradeoffs=_coerce_list(stakeholder_payload.get("tradeoffs")),
                raw_response=raw_response,
            )
        )

    stakeholder_inputs = [
        {
            "stakeholder": run.name,
            "goals": run.goals,
            "needs": run.needs,
            "concerns": run.concerns,
            "priorities": run.priorities,
            "constraints": run.constraints,
            "tradeoffs": run.tradeoffs,
        }
        for run in stakeholder_runs
    ]

    system_prompt = render_prompt(engineer_prompt_dir / "system.txt")
    user_prompt_1 = render_prompt(
        engineer_prompt_dir / "step1_user.txt",
        system_description=system_description,
        stakeholder_inputs_json=json.dumps(stakeholder_inputs, ensure_ascii=False),
    )
    r1, raw_response_1, time_1 = _call_and_parse(
        model_func,
        model_name,
        system_prompt,
        user_prompt_1,
        step="engineer-step1",
    )
    log_experiment_to_csv(
        "r2-multi-stakeholder.csv",
        "Requirements-Step1",
        model_name,
        "multi-stakeholder",
        iteration,
        user_prompt_1,
        raw_response_1,
        time_1,
    )

    user_prompt_2 = render_prompt(
        engineer_prompt_dir / "step2_user.txt",
        system_description=system_description,
        stakeholder_inputs_json=json.dumps(stakeholder_inputs, ensure_ascii=False),
        step1_json=json.dumps(r1, ensure_ascii=False),
    )
    r2, raw_response_2, time_2 = _call_and_parse(
        model_func,
        model_name,
        system_prompt,
        user_prompt_2,
        step="engineer-step2",
    )
    log_experiment_to_csv(
        "r2-multi-stakeholder.csv",
        "Requirements-Step2",
        model_name,
        "multi-stakeholder",
        iteration,
        user_prompt_2,
        raw_response_2,
        time_2,
    )

    user_prompt_3 = render_prompt(
        engineer_prompt_dir / "step3_user.txt",
        user_stories_json=json.dumps(r2.get("user_stories", []), ensure_ascii=False),
    )
    r3, raw_response_3, time_3 = _call_and_parse(
        model_func,
        model_name,
        system_prompt,
        user_prompt_3,
        step="engineer-step3",
    )
    log_experiment_to_csv(
        "r2-multi-stakeholder.csv",
        "Requirements-Step3",
        model_name,
        "multi-stakeholder",
        iteration,
        user_prompt_3,
        raw_response_3,
        time_3,
    )

    prompt_log = (
        f"[SYSTEM]\n{system_prompt}\n\n"
        f"[STAKEHOLDERS]\n{json.dumps(stakeholder_inputs, ensure_ascii=False)}\n\n"
        f"[STEP1]\n{user_prompt_1}\n\n"
        f"[STEP2]\n{user_prompt_2}\n\n"
        f"[STEP3]\n{user_prompt_3}"
    )

    raw_artifact = {
        **r1,
        **r2,
        **r3,
        "metadata": {
            "version": "llm",
            "case_study": case_study,
            "model_used": model_name,
            "prompt_log": prompt_log,
        },
    }

    artifact = None
    try:
        artifact = RequirementsArtifact.model_validate(raw_artifact)
        save_artifact(
            artifact.model_dump(),
            f"artifact_r2_multi_{model_name.split('-')[0]}_{case_study}.json",
        )
    except ValidationError as exc:
        print(f"[ERROR] Pydantic validation failed:\n{exc}")

    artifact_json = json.dumps(raw_artifact, ensure_ascii=False)
    traceability_user_prompt = render_prompt(
        traceability_prompt,
        system_description=system_description,
        stakeholder_inputs_json=json.dumps(stakeholder_inputs, ensure_ascii=False),
        artifact_json=artifact_json,
    )
    traceability_payload, traceability_raw, traceability_time = _call_and_parse(
        model_func,
        model_name,
        system_prompt,
        traceability_user_prompt,
        step="traceability",
    )
    log_experiment_to_csv(
        "r2-multi-stakeholder.csv",
        "Traceability",
        model_name,
        "multi-stakeholder",
        iteration,
        traceability_user_prompt,
        traceability_raw,
        traceability_time,
    )

    stakeholder_evaluations: list[dict] = []
    evaluator_system = render_prompt(evaluator_system_prompt)
    for agent_path in agent_paths:
        stakeholder_name = Path(agent_path).stem
        stakeholder_profile = Path(agent_path).read_text(encoding="utf-8")
        eval_prompt = render_prompt(
            evaluator_prompt,
            system_description=system_description,
            stakeholder_profile=stakeholder_profile,
            stakeholder_name=stakeholder_name,
            artifact_json=artifact_json,
        )
        eval_payload, eval_raw, eval_time = _call_and_parse(
            model_func,
            model_name,
            evaluator_system,
            eval_prompt,
            step=f"evaluation-{stakeholder_name}",
        )
        log_experiment_to_csv(
            "r2-multi-stakeholder.csv",
            f"Evaluation-{stakeholder_name}",
            model_name,
            "multi-stakeholder",
            iteration,
            eval_prompt,
            eval_raw,
            eval_time,
        )
        stakeholder_evaluations.append(eval_payload)

    save_artifact(
        {
            "stakeholder_runs": stakeholder_inputs,
            "traceability": traceability_payload,
            "stakeholder_evaluations": stakeholder_evaluations,
        },
        f"artifact_r2_multi_{model_name.split('-')[0]}_{case_study}_supplement.json",
    )

    return OrchestrationResult(
        stakeholder_runs=stakeholder_runs,
        requirements_artifact=raw_artifact,
        traceability=traceability_payload,
        stakeholder_evaluations=stakeholder_evaluations,
    )


def _default_stakeholder_paths() -> list[str]:
    agent_dir = Path("agents")
    return [
        str(agent_dir / "business.md"),
        str(agent_dir / "security.md"),
        str(agent_dir / "ux.md"),
        str(agent_dir / "qa.md"),
    ]


def _call_and_parse(
    model_func,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    step: str,
    retries: int = 3,
) -> tuple[dict, str, float]:
    for attempt in range(retries):
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
                print(
                    f"[WARN] Step {step}, attempt {attempt + 1}: invalid JSON, retry..."
                )
                print(f"[DEBUG] Raw response:\n{response}\n")
    print(f"[ERROR] Step {step}: failed after {retries} attempts")
    return {}, "", 0.0


def _coerce_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]
