from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable
import time

from datetime import datetime, timezone
import os

from pydantic import ValidationError

import hashlib

from evaluator import (
    build_evaluation_payload,
    DEFAULT_EVALUATION_RUBRIC,
    _match_any_concern,
)
from schemas.requirements_artifact import RequirementsArtifact
from utils.json_saver import save_artifact
from utils.logger import log_experiment_to_csv
from utils.normalizer import normalize_artifact
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
    negotiation_prompt_dir = prompt_root / "negotiation"
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
            # "weighted_concerns": run.weighted_concerns,
            "priorities": run.priorities,
            "constraints": run.constraints,
            "tradeoffs": run.tradeoffs,
        }
        for run in stakeholder_runs
    ]

    system_prompt = render_prompt(engineer_prompt_dir / "system.txt")
    stakeholder_system_prompt = render_prompt(agent_prompt_dir / "system.txt")
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

    stakeholder_importance = _load_stakeholder_importance()
    negotiation_history: list[dict] = []
    max_iterations = int(os.getenv("SDLC_NEGOTIATION_MAX_ITERS", "2"))
    utility_epsilon = float(os.getenv("SDLC_NEGOTIATION_EPSILON", "0.02"))
    previous_utility = None

    for iteration_index in range(1, max_iterations + 1):
        impacts: list[dict] = []
        proposals: list[dict] = []
        negotiation_focus = _build_negotiation_focus(
            artifact=raw_artifact,
            stakeholder_inputs=stakeholder_inputs,
            stakeholder_importance=stakeholder_importance,
            top_k=int(os.getenv("SDLC_NEGOTIATION_FOCUS_TOPK", "3")),
        )

        for agent_path in agent_paths:
            stakeholder_name = Path(agent_path).stem
            stakeholder_profile = Path(agent_path).read_text(encoding="utf-8")
            impact_prompt = render_prompt(
                negotiation_prompt_dir / "impact.txt",
                system_description=system_description,
                stakeholder_profile=stakeholder_profile,
                artifact_json=json.dumps(raw_artifact, ensure_ascii=False),
            )
            impact_payload, impact_raw, impact_time = _call_and_parse(
                model_func,
                model_name,
                stakeholder_system_prompt,
                impact_prompt,
                step=f"negotiation-impact-{stakeholder_name}-{iteration_index}",
            )
            log_experiment_to_csv(
                "r2-multi-stakeholder.csv",
                f"Negotiation-Impact-{stakeholder_name}-{iteration_index}",
                model_name,
                "multi-stakeholder",
                iteration,
                impact_prompt,
                impact_raw,
                impact_time,
            )
            impact_payload["stakeholder"] = stakeholder_name
            impacts.append(impact_payload)

            proposal_prompt = render_prompt(
                negotiation_prompt_dir / "proposals.txt",
                system_description=system_description,
                stakeholder_profile=stakeholder_profile,
                artifact_json=json.dumps(raw_artifact, ensure_ascii=False),
                impact_json=json.dumps(impact_payload, ensure_ascii=False),
            )
            proposal_payload, proposal_raw, proposal_time = _call_and_parse(
                model_func,
                model_name,
                stakeholder_system_prompt,
                proposal_prompt,
                step=f"negotiation-proposals-{stakeholder_name}-{iteration_index}",
            )
            log_experiment_to_csv(
                "r2-multi-stakeholder.csv",
                f"Negotiation-Proposals-{stakeholder_name}-{iteration_index}",
                model_name,
                "multi-stakeholder",
                iteration,
                proposal_prompt,
                proposal_raw,
                proposal_time,
            )
            proposal_payload["stakeholder"] = stakeholder_name
            proposals.append(proposal_payload)

        negotiation_inputs = {
            "impacts": impacts,
            "proposals": proposals,
        }

        neg_prompt_1 = render_prompt(
            negotiation_prompt_dir / "step1_user.txt",
            system_description=system_description,
            stakeholder_inputs_json=json.dumps(
                stakeholder_inputs_for_engineer, ensure_ascii=False
            ),
            artifact_json=json.dumps(raw_artifact, ensure_ascii=False),
            negotiation_inputs_json=json.dumps(negotiation_inputs, ensure_ascii=False),
            negotiation_focus_json=json.dumps(negotiation_focus, ensure_ascii=False),
        )
        neg_r1, neg_raw_1, neg_time_1 = _call_and_parse(
            model_func,
            model_name,
            system_prompt,
            neg_prompt_1,
            step=f"negotiation-step1-{iteration_index}",
        )
        log_experiment_to_csv(
            "r2-multi-stakeholder.csv",
            f"Negotiation-Step1-{iteration_index}",
            model_name,
            "multi-stakeholder",
            iteration,
            neg_prompt_1,
            neg_raw_1,
            neg_time_1,
        )

        neg_prompt_2 = render_prompt(
            negotiation_prompt_dir / "step2_nfr_user.txt",
            system_description=system_description,
            stakeholder_inputs_json=json.dumps(
                stakeholder_inputs_for_engineer, ensure_ascii=False
            ),
            artifact_json=json.dumps(raw_artifact, ensure_ascii=False),
            negotiation_inputs_json=json.dumps(negotiation_inputs, ensure_ascii=False),
            negotiation_focus_json=json.dumps(negotiation_focus, ensure_ascii=False),
            step1_json=json.dumps(neg_r1, ensure_ascii=False),
        )
        neg_r2, neg_raw_2, neg_time_2 = _call_and_parse(
            model_func,
            model_name,
            system_prompt,
            neg_prompt_2,
            step=f"negotiation-step2-{iteration_index}",
        )
        log_experiment_to_csv(
            "r2-multi-stakeholder.csv",
            f"Negotiation-Step2-{iteration_index}",
            model_name,
            "multi-stakeholder",
            iteration,
            neg_prompt_2,
            neg_raw_2,
            neg_time_2,
        )

        neg_prompt_3 = render_prompt(
            negotiation_prompt_dir / "step3_userstories_user.txt",
            system_description=system_description,
            stakeholder_inputs_json=json.dumps(
                stakeholder_inputs_for_engineer, ensure_ascii=False
            ),
            artifact_json=json.dumps(raw_artifact, ensure_ascii=False),
            negotiation_inputs_json=json.dumps(negotiation_inputs, ensure_ascii=False),
            negotiation_focus_json=json.dumps(negotiation_focus, ensure_ascii=False),
            step1_json=json.dumps(neg_r1, ensure_ascii=False),
            step2_json=json.dumps(neg_r2, ensure_ascii=False),
        )
        neg_r3, neg_raw_3, neg_time_3 = _call_and_parse(
            model_func,
            model_name,
            system_prompt,
            neg_prompt_3,
            step=f"negotiation-step3-{iteration_index}",
        )
        log_experiment_to_csv(
            "r2-multi-stakeholder.csv",
            f"Negotiation-Step3-{iteration_index}",
            model_name,
            "multi-stakeholder",
            iteration,
            neg_prompt_3,
            neg_raw_3,
            neg_time_3,
        )

        neg_prompt_4 = render_prompt(
            negotiation_prompt_dir / "step4_acceptance_user.txt",
            artifact_json=json.dumps(raw_artifact, ensure_ascii=False),
            negotiation_inputs_json=json.dumps(negotiation_inputs, ensure_ascii=False),
            negotiation_focus_json=json.dumps(negotiation_focus, ensure_ascii=False),
            user_stories_json=json.dumps(neg_r3.get("user_stories", []), ensure_ascii=False),
        )
        neg_r4, neg_raw_4, neg_time_4 = _call_and_parse(
            model_func,
            model_name,
            system_prompt,
            neg_prompt_4,
            step=f"negotiation-step4-{iteration_index}",
        )
        log_experiment_to_csv(
            "r2-multi-stakeholder.csv",
            f"Negotiation-Step4-{iteration_index}",
            model_name,
            "multi-stakeholder",
            iteration,
            neg_prompt_4,
            neg_raw_4,
            neg_time_4,
        )

        updated_artifact = {
            **neg_r1,
            **neg_r2,
            **neg_r3,
            **neg_r4,
            "metadata": {
                "version": "llm",
                "case_study": case_study,
                "model_used": model_name,
                "prompt_log": prompt_log,
            },
        }

        conflict_prompt = render_prompt(
            negotiation_prompt_dir / "conflict_table.txt",
            system_description=system_description,
            stakeholder_inputs_json=json.dumps(
                stakeholder_inputs_for_engineer, ensure_ascii=False
            ),
            negotiation_inputs_json=json.dumps(negotiation_inputs, ensure_ascii=False),
            negotiation_focus_json=json.dumps(negotiation_focus, ensure_ascii=False),
            artifact_json=json.dumps(updated_artifact, ensure_ascii=False),
        )
        conflict_payload, conflict_raw, conflict_time = _call_and_parse(
            model_func,
            model_name,
            system_prompt,
            conflict_prompt,
            step=f"negotiation-conflicts-{iteration_index}",
        )
        log_experiment_to_csv(
            "r2-multi-stakeholder.csv",
            f"Negotiation-Conflicts-{iteration_index}",
            model_name,
            "multi-stakeholder",
            iteration,
            conflict_prompt,
            conflict_raw,
            conflict_time,
        )

        normalized_iteration, _ = normalize_artifact(updated_artifact)
        iteration_eval = build_evaluation_payload(
            artifact=normalized_iteration,
            stakeholder_inputs=stakeholder_inputs,
            traceability={"by_requirement": {}},
            stakeholder_importance=stakeholder_importance,
            evaluation_rubric=DEFAULT_EVALUATION_RUBRIC,
        )
        current_utility = iteration_eval["raw_metrics"]["utility"]
        delta = None if previous_utility is None else current_utility - previous_utility

        negotiation_history.append(
            {
                "iteration": iteration_index,
                "impacts": impacts,
                "proposals": proposals,
                "conflict_resolution_table": conflict_payload.get(
                    "conflict_resolution_table", []
                ),
                "utility": current_utility,
                "delta_utility": delta,
            }
        )

        raw_artifact = updated_artifact
        previous_utility = current_utility

        if delta is not None and abs(delta) < utility_epsilon:
            break

    artifact = None
    try:
        artifact = RequirementsArtifact.model_validate(raw_artifact)
        save_artifact(
            artifact.model_dump(),
            f"artifact_r2_multi_{model_name.split('-')[0]}_{case_study}.json",
        )
    except ValidationError as exc:
        print(f"[ERROR] Pydantic validation failed:\n{exc}")

    normalized_artifact, normalization_report = normalize_artifact(raw_artifact)
    artifact_json = json.dumps(raw_artifact, ensure_ascii=False)
    evaluator_system = render_prompt(evaluator_system_prompt)
    requirement_summaries = _summarize_requirements(normalized_artifact)
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
        stakeholder_summary = _build_stakeholder_eval_summary(
            stakeholder_name=stakeholder_name,
            stakeholder_profile=stakeholder_profile,
            artifact=normalized_artifact,
            stakeholder_inputs=stakeholder_inputs,
        )
        eval_prompt = render_prompt(
            evaluator_prompt,
            system_description=system_description,
            stakeholder_profile=stakeholder_profile,
            stakeholder_name=stakeholder_name,
            artifact_json=json.dumps(stakeholder_summary, ensure_ascii=False),
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

    evaluation_payload = build_evaluation_payload(
        artifact=normalized_artifact,
        stakeholder_inputs=stakeholder_inputs,
        traceability=traceability_payload,
        stakeholder_importance=stakeholder_importance,
        evaluation_rubric=DEFAULT_EVALUATION_RUBRIC,
    )

    evaluator_prompt_hash = _hash_text(
        (evaluator_system_prompt.read_text(encoding="utf-8")
        + evaluator_prompt.read_text(encoding="utf-8"))
    )
    traceability_prompt_hash = _hash_text(
        traceability_prompt.read_text(encoding="utf-8")
    )

    save_artifact(
        {
            "stakeholder_runs": stakeholder_inputs,
            "traceability": traceability_payload,
            "stakeholder_evaluations": stakeholder_evaluations,
            "evaluation": evaluation_payload,
            "normalized_artifact": normalized_artifact,
            "normalization_report": normalization_report,
            "negotiation": {
                "history": negotiation_history,
                "max_iterations": max_iterations,
                "utility_epsilon": utility_epsilon,
            },
            "experiment_config": {
                "generator_model": model_name,
                "evaluator_model": evaluator_model_name,
                "evaluation_timestamp": _utc_now_iso(),
                "stakeholder_importance": stakeholder_importance,
                "rubric": DEFAULT_EVALUATION_RUBRIC,
                "evaluation_policy": _evaluation_policy_summary(),
                "validity_notes": _validity_notes(),
                "evaluator_prompt_hash": evaluator_prompt_hash,
                "traceability_prompt_hash": traceability_prompt_hash,
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
            parsed = _parse_json_response(response)
            if parsed is not None:
                return parsed, response, elapsed
            raise json.JSONDecodeError("Invalid JSON", response, 0)
        except json.JSONDecodeError:
            try:
                import ast

                fixed = ast.literal_eval(_strip_code_fences(response))
                return fixed, response, elapsed
            except Exception:
                print(
                    f"[WARN] Step {step}, attempt {attempt + 1}: invalid JSON, retry..."
                )
                print(f"[DEBUG] Raw response:\n{response}\n")
    print(f"[ERROR] Step {step}: failed after {retries} attempts")
    return {}, "", 0.0


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
    return stripped.strip()


def _parse_json_response(text: str) -> dict | list | None:
    stripped = _strip_code_fences(text)
    decoder = json.JSONDecoder()
    try:
        return decoder.decode(stripped)
    except json.JSONDecodeError:
        pass
    try:
        obj, _ = decoder.raw_decode(stripped.lstrip())
        return obj
    except json.JSONDecodeError:
        pass
    fragment = _extract_balanced_json(stripped)
    if fragment:
        try:
            return decoder.decode(fragment)
        except json.JSONDecodeError:
            return None
    return None


def _extract_balanced_json(text: str) -> str:
    start = None
    stack: list[str] = []
    in_string = False
    escape = False

    for index, char in enumerate(text):
        if start is None:
            if char in "{[":
                start = index
                stack.append(char)
            continue

        if in_string:
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue
        if char in "{[":
            stack.append(char)
            continue
        if char in "}]":
            if not stack:
                break
            opener = stack.pop()
            if (opener == "{" and char != "}") or (opener == "[" and char != "]"):
                break
            if not stack:
                return text[start : index + 1]

    return ""


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


def _build_stakeholder_eval_summary(
    stakeholder_name: str,
    stakeholder_profile: str,
    artifact: dict,
    stakeholder_inputs: list[dict],
) -> dict:
    relevant_concerns = _get_stakeholder_concerns(stakeholder_name, stakeholder_inputs)
    matched_requirement_ids = _match_requirements_for_concerns(artifact, relevant_concerns)
    return {
        "stakeholder": stakeholder_name,
        "profile": _truncate_text(stakeholder_profile, 1200),
        "concerns": relevant_concerns,
        "matched_requirement_ids": matched_requirement_ids,
        "artifact_summary": _summarize_requirements_subset(
            artifact,
            matched_requirement_ids,
        ),
    }


def _build_negotiation_focus(
    artifact: dict,
    stakeholder_inputs: list[dict],
    stakeholder_importance: dict[str, float],
    top_k: int = 3,
) -> dict:
    normalized_artifact, _ = normalize_artifact(artifact)
    evaluation = build_evaluation_payload(
        artifact=normalized_artifact,
        stakeholder_inputs=stakeholder_inputs,
        traceability={"by_requirement": {}},
        stakeholder_importance=stakeholder_importance,
        evaluation_rubric=DEFAULT_EVALUATION_RUBRIC,
    )

    unresolved = [
        item
        for item in evaluation.get("per_concern_matrix", [])
        if item.get("status") in {"unsatisfied", "partially_satisfied"}
    ]
    unresolved.sort(
        key=lambda item: (
            0 if item.get("status") == "unsatisfied" else 1,
            str(item.get("stakeholder", "")),
            str(item.get("concern", "")),
        )
    )

    focus_concerns: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in unresolved:
        stakeholder = str(item.get("stakeholder", "")).strip()
        concern = str(item.get("concern", "")).strip()
        key = (stakeholder, concern)
        if not stakeholder or not concern or key in seen:
            continue
        seen.add(key)
        focus_concerns.append(
            {
                "stakeholder": stakeholder,
                "concern": _truncate_text(concern, 160),
                "status": item.get("status", "unsatisfied"),
            }
        )
        if len(focus_concerns) >= max(top_k, 1):
            break

    lowest_stakeholders = [
        str(item.get("stakeholder", "")).strip()
        for item in sorted(
            evaluation.get("stakeholder_scores", []),
            key=lambda row: float(row.get("satisfaction", 0.0)),
        )
        if str(item.get("stakeholder", "")).strip()
    ][:2]

    return {
        "focus_concerns": focus_concerns,
        "lowest_satisfaction_stakeholders": lowest_stakeholders,
        "guidance": "Priorytetyzuj minimalne zmiany adresujace focus_concerns i balans satysfakcji.",
    }


def _get_stakeholder_concerns(
    stakeholder_name: str,
    stakeholder_inputs: list[dict],
) -> list[str]:
    for stakeholder in stakeholder_inputs:
        if str(stakeholder.get("stakeholder", "")) != stakeholder_name:
            continue
        concerns = stakeholder.get("weighted_concerns") or stakeholder.get("concerns") or []
        if concerns and isinstance(concerns[0], dict):
            return [str(item.get("concern", "")) for item in concerns if item.get("concern")]
        return [str(item) for item in concerns if item]
    return []


def _match_requirements_for_concerns(artifact: dict, concerns: list[str]) -> list[str]:
    if not concerns:
        return []
    requirement_items = _collect_requirement_items(artifact)
    matched: list[str] = []
    for item in requirement_items:
        text = item.get("text", "")
        if _match_any_concern(text, concerns, DEFAULT_EVALUATION_RUBRIC):
            matched.append(str(item.get("id", "")))
    return matched[:20]


def _summarize_requirements_subset(artifact: dict, requirement_ids: list[str]) -> list[dict]:
    if not requirement_ids:
        return _summarize_requirements(artifact, max_len=100)[:12]
    requirement_id_set = set(requirement_ids)
    summaries: list[dict] = []
    for item in _collect_requirement_items(artifact):
        if str(item.get("id", "")) not in requirement_id_set:
            continue
        summaries.append(
            {
                "id": item.get("id", ""),
                "type": item.get("type", ""),
                "text": _truncate_text(item.get("text", ""), 140),
            }
        )
    return summaries[:20]


def _collect_requirement_items(artifact: dict) -> list[dict]:
    items: list[dict] = []
    for req in artifact.get("functional_requirements", []):
        items.append(
            {"id": req.get("id", ""), "type": "FR", "text": req.get("description", "")}
        )
    for req in artifact.get("non_functional_requirements", []):
        items.append(
            {"id": req.get("id", ""), "type": "NFR", "text": req.get("description", "")}
        )
    for req in artifact.get("user_stories", []):
        items.append(
            {"id": req.get("id", ""), "type": "US", "text": req.get("description", "")}
        )
    for req in artifact.get("acceptance_criteria", []):
        text = " ".join(
            str(part)
            for part in [req.get("given"), req.get("when"), req.get("then")]
            if part
        )
        items.append({"id": req.get("id", ""), "type": "AC", "text": text})
    return items


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


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
