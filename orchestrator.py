from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable
import time

from datetime import datetime, timezone
import os

from pydantic import ValidationError

from evaluator import build_evaluation_payload, DEFAULT_EVALUATION_RUBRIC
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
    weighted_concerns: list[dict]
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
    evaluation: dict


def run_multi_stakeholder_experiment(
    model_func,
    model_name: str,
    evaluator_model_func,
    evaluator_model_name: str,
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
                weighted_concerns=_coerce_weighted_concerns(
                    stakeholder_payload.get("weighted_concerns")
                ),
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
            "weighted_concerns": run.weighted_concerns,
            "priorities": run.priorities,
            "constraints": run.constraints,
            "tradeoffs": run.tradeoffs,
        }
        for run in stakeholder_runs
    ]

    stakeholder_inputs_for_engineer = [
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
        stakeholder_inputs_json=json.dumps(
            stakeholder_inputs_for_engineer, ensure_ascii=False
        ),
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
        stakeholder_inputs_json=json.dumps(
            stakeholder_inputs_for_engineer, ensure_ascii=False
        ),
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
        f"[STAKEHOLDERS]\n{json.dumps(stakeholder_inputs_for_engineer, ensure_ascii=False)}\n\n"
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
    evaluator_system = render_prompt(evaluator_system_prompt)
    requirement_summaries = _summarize_requirements(raw_artifact)
    traceability_payload = {"by_requirement": {}}

    for index, chunk in enumerate(_chunk_list(requirement_summaries, 10), start=1):
        traceability_user_prompt = render_prompt(
            traceability_prompt,
            system_description=system_description,
            stakeholder_inputs_json=json.dumps(
                stakeholder_inputs_for_engineer, ensure_ascii=False
            ),
            requirements_subset_json=json.dumps(chunk, ensure_ascii=False),
        )
        chunk_payload, traceability_raw, traceability_time = _call_and_parse(
            evaluator_model_func,
            evaluator_model_name,
            evaluator_system,
            traceability_user_prompt,
            step=f"traceability-{index}",
        )
        log_experiment_to_csv(
            "r2-multi-stakeholder.csv",
            f"Traceability-{index}",
            evaluator_model_name,
            "multi-stakeholder",
            iteration,
            traceability_user_prompt,
            traceability_raw,
            traceability_time,
        )
        traceability_payload = _merge_traceability(traceability_payload, chunk_payload)

    stakeholder_evaluations: list[dict] = []
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
            evaluator_model_func,
            evaluator_model_name,
            evaluator_system,
            eval_prompt,
            step=f"evaluation-{stakeholder_name}",
        )
        log_experiment_to_csv(
            "r2-multi-stakeholder.csv",
            f"Evaluation-{stakeholder_name}",
            evaluator_model_name,
            "multi-stakeholder",
            iteration,
            eval_prompt,
            eval_raw,
            eval_time,
        )
        stakeholder_evaluations.append(eval_payload)

    stakeholder_importance = _load_stakeholder_importance()
    evaluation_payload = build_evaluation_payload(
        artifact=raw_artifact,
        stakeholder_inputs=stakeholder_inputs,
        traceability=traceability_payload,
        stakeholder_importance=stakeholder_importance,
        evaluation_rubric=DEFAULT_EVALUATION_RUBRIC,
    )

    save_artifact(
        {
            "stakeholder_runs": stakeholder_inputs,
            "traceability": traceability_payload,
            "stakeholder_evaluations": stakeholder_evaluations,
            "evaluation": evaluation_payload,
            "experiment_config": {
                "generator_model": model_name,
                "evaluator_model": evaluator_model_name,
                "evaluation_timestamp": _utc_now_iso(),
                "stakeholder_importance": stakeholder_importance,
                "rubric": DEFAULT_EVALUATION_RUBRIC,
                "evaluation_policy": _evaluation_policy_summary(),
                "validity_notes": _validity_notes(),
            },
        },
        f"artifact_r2_multi_{model_name.split('-')[0]}_{case_study}_supplement.json",
    )

    return OrchestrationResult(
        stakeholder_runs=stakeholder_runs,
        requirements_artifact=raw_artifact,
        traceability=traceability_payload,
        stakeholder_evaluations=stakeholder_evaluations,
        evaluation=evaluation_payload,
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


def _coerce_weighted_concerns(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    cleaned: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        concern = str(item.get("concern", "")).strip()
        weight = item.get("weight", 0)
        try:
            weight = float(weight)
        except (TypeError, ValueError):
            weight = 0.0
        if concern:
            cleaned.append({"concern": concern, "weight": weight})
    return cleaned


def _load_stakeholder_importance() -> dict[str, float]:
    raw = os.getenv("SDLC_STAKEHOLDER_IMPORTANCE", "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    importance: dict[str, float] = {}
    for key, value in data.items():
        try:
            importance[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return importance


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _evaluation_policy_summary() -> dict:
    return {
        "satisfied_requires": [
            "explicit requirement",
            "traceable to concern",
            "measurable/testable where applicable",
            "no contradictions",
        ],
        "penalize": [
            "vague requirements",
            "implied support",
            "missing acceptance criteria",
            "unresolved conflicts",
            "unsupported assumptions",
            "missing traceability",
        ],
    }


def _summarize_requirements(artifact: dict, max_len: int = 160) -> list[dict]:
    summaries: list[dict] = []
    for item in artifact.get("functional_requirements", []):
        summaries.append(
            {
                "id": item.get("id", ""),
                "type": "FR",
                "text": _truncate_text(item.get("description", ""), max_len),
            }
        )
    for item in artifact.get("non_functional_requirements", []):
        summaries.append(
            {
                "id": item.get("id", ""),
                "type": "NFR",
                "text": _truncate_text(item.get("description", ""), max_len),
            }
        )
    for item in artifact.get("user_stories", []):
        summaries.append(
            {
                "id": item.get("id", ""),
                "type": "US",
                "text": _truncate_text(item.get("description", ""), max_len),
            }
        )
    for item in artifact.get("acceptance_criteria", []):
        text = " ".join(
            str(part)
            for part in [item.get("given"), item.get("when"), item.get("then")]
            if part
        )
        summaries.append(
            {
                "id": item.get("id", ""),
                "type": "AC",
                "text": _truncate_text(text, max_len),
            }
        )
    return summaries


def _truncate_text(text: str, max_len: int) -> str:
    text = str(text).strip()
    if len(text) <= max_len:
        return text
    return f"{text[: max_len - 3]}..."


def _chunk_list(items: list[dict], size: int) -> list[list[dict]]:
    if size <= 0:
        return [items]
    return [items[i : i + size] for i in range(0, len(items), size)]


def _merge_traceability(base: dict, incoming: dict) -> dict:
    merged = {"by_requirement": {**base.get("by_requirement", {})}}
    incoming_map = incoming.get("by_requirement", {}) if isinstance(incoming, dict) else {}
    for req_id, stakeholders in incoming_map.items():
        if not isinstance(stakeholders, list):
            continue
        merged["by_requirement"][req_id] = list({str(s) for s in stakeholders if s})
    return merged


def _validity_notes() -> dict:
    return {
        "limitations": [
            "Rule-based metrics may miss semantic matches",
            "LLM evaluator may still share latent assumptions",
            "Conflict detection uses keyword heuristics",
        ],
        "bias_risks": [
            "Evaluator prompt wording can influence severity",
            "Stakeholder profiles may bias concern phrasing",
        ],
        "mitigations": [
            "Cross-model evaluation supported",
            "Deterministic metrics reported alongside LLM judgments",
        ],
    }
