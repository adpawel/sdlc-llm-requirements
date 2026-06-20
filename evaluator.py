from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Iterable


@dataclass(frozen=True)
class EvaluationResult:
    concern_coverage: float
    weighted_concern_coverage: float
    traceability_completeness: float
    conflict_preservation: float
    requirement_specificity: float
    acceptance_criteria_testability: float
    requirement_ambiguity: float
    hallucination_rate: float
    stakeholder_satisfaction: float
    fairness_score: float
    satisfaction_variance: float
    min_satisfaction: float
    utility: float
    utility_under_conflict: float
    timestamp: str


DEFAULT_EVALUATION_RUBRIC = {
    "policy": {
        "satisfied": [
            "explicit representation",
            "traceable to requirement",
            "measurable or testable when applicable",
            "not contradicted elsewhere",
        ],
        "partially_satisfied": [
            "partially addressed",
            "implied but not explicit",
            "missing measurable criteria",
            "minor conflicts unresolved",
        ],
        "unsatisfied": [
            "missing",
            "contradicted",
            "unsupported assumptions",
        ],
    },
    "thresholds": {
        "token_overlap": 1,
        "specificity_min": 0.4,
        "testability_min": 0.5,
    },
    "ambiguity_terms": [
        "szybko",
        "latwo",
        "intuicyj",
        "przyjazn",
        "w miare",
        "itp",
        "etc",
        "zwykle",
        "zazwyczaj",
        "jakos",
        "wystarczajaco",
        "gdzie mozliwe",
        "tam gdzie mozliwe",
        "optymaln",
        "wydajn",
        "elastyczn",
    ],
}


def evaluate_requirements_artifact(
    artifact: dict,
    stakeholder_inputs: list[dict],
    traceability: dict,
    stakeholder_importance: dict[str, float] | None = None,
    evaluation_rubric: dict | None = None,
) -> EvaluationResult:
    """Evaluate an artifact against deterministic and hybrid metrics."""
    rubric = evaluation_rubric or DEFAULT_EVALUATION_RUBRIC
    requirements = _collect_requirements(artifact)
    requirement_texts = {req["id"]: req["text"] for req in requirements}

    concern_map = _build_concern_map(stakeholder_inputs)
    concern_coverage, weighted_coverage, uncovered = _compute_concern_coverage(
        concern_map,
        requirement_texts,
        rubric,
    )

    traceability_completeness = _compute_traceability_completeness(
        requirement_texts,
        concern_map,
        rubric,
    )

    hallucination_rate, hallucinated = _compute_hallucination_rate(
        requirement_texts,
        stakeholder_inputs,
        rubric,
    )

    requirement_specificity = _compute_requirement_specificity(requirements, rubric)
    acceptance_testability = _compute_acceptance_testability(
        artifact.get("acceptance_criteria", []),
        rubric,
    )
    requirement_ambiguity = _compute_requirement_ambiguity(requirements, rubric)

    conflict_preservation, conflict_summaries = _compute_conflict_preservation(
        stakeholder_inputs,
        requirement_texts,
    )

    stakeholder_importance = stakeholder_importance or {}
    stakeholder_scores = _compute_stakeholder_satisfaction(
        concern_map,
        requirement_texts,
        stakeholder_importance,
        rubric,
    )

    utility, fairness_score, variance, min_satisfaction = _compute_utility_metrics(
        stakeholder_scores
    )

    utility_under_conflict = utility * (1 - (1 - conflict_preservation) * 0.5)

    return EvaluationResult(
        concern_coverage=concern_coverage,
        weighted_concern_coverage=weighted_coverage,
        traceability_completeness=traceability_completeness,
        conflict_preservation=conflict_preservation,
        requirement_specificity=requirement_specificity,
        acceptance_criteria_testability=acceptance_testability,
        requirement_ambiguity=requirement_ambiguity,
        hallucination_rate=hallucination_rate,
        stakeholder_satisfaction=utility,
        fairness_score=fairness_score,
        satisfaction_variance=variance,
        min_satisfaction=min_satisfaction,
        utility=utility,
        utility_under_conflict=utility_under_conflict,
        timestamp=_utc_now_iso(),
    )


def build_evaluation_payload(
    artifact: dict,
    stakeholder_inputs: list[dict],
    traceability: dict,
    stakeholder_importance: dict[str, float] | None = None,
    evaluation_rubric: dict | None = None,
) -> dict:
    rubric = evaluation_rubric or DEFAULT_EVALUATION_RUBRIC
    requirements = _collect_requirements(artifact)
    requirement_texts = {req["id"]: req["text"] for req in requirements}
    concern_map = _build_concern_map(stakeholder_inputs)

    concern_coverage, weighted_coverage, uncovered = _compute_concern_coverage(
        concern_map,
        requirement_texts,
        rubric,
    )
    traceability_completeness = _compute_traceability_completeness(
        requirement_texts,
        concern_map,
        rubric,
    )
    hallucination_rate, hallucinated = _compute_hallucination_rate(
        requirement_texts,
        stakeholder_inputs,
        rubric,
    )
    conflict_preservation, conflict_summaries = _compute_conflict_preservation(
        stakeholder_inputs,
        requirement_texts,
    )

    requirement_specificity = _compute_requirement_specificity(requirements, rubric)
    acceptance_testability = _compute_acceptance_testability(
        artifact.get("acceptance_criteria", []),
        rubric,
    )
    requirement_ambiguity = _compute_requirement_ambiguity(requirements, rubric)

    stakeholder_importance = stakeholder_importance or {}
    per_concern_matrix = _compute_per_concern_matrix(
        concern_map,
        requirement_texts,
        rubric,
    )
    stakeholder_scores = _compute_stakeholder_satisfaction(
        concern_map,
        requirement_texts,
        stakeholder_importance,
        rubric,
    )
    utility, fairness_score, variance, min_satisfaction = _compute_utility_metrics(
        stakeholder_scores
    )
    utility_under_conflict = utility * (1 - (1 - conflict_preservation) * 0.5)

    return {
        "raw_metrics": {
            "concern_coverage": concern_coverage,
            "weighted_concern_coverage": weighted_coverage,
            "traceability_completeness": traceability_completeness,
            "conflict_preservation": conflict_preservation,
            "requirement_specificity": requirement_specificity,
            "acceptance_criteria_testability": acceptance_testability,
            "requirement_ambiguity": requirement_ambiguity,
            "hallucination_rate": hallucination_rate,
            "utility": utility,
            "utility_under_conflict": utility_under_conflict,
            "fairness_score": fairness_score,
            "satisfaction_variance": variance,
            "min_satisfaction": min_satisfaction,
        },
        "per_concern_matrix": per_concern_matrix,
        "normalized_metrics": {
            "concern_coverage": concern_coverage,
            "weighted_concern_coverage": weighted_coverage,
            "traceability_completeness": traceability_completeness,
            "conflict_preservation": conflict_preservation,
            "requirement_specificity": requirement_specificity,
            "acceptance_criteria_testability": acceptance_testability,
            "requirement_ambiguity": requirement_ambiguity,
            "hallucination_rate": hallucination_rate,
            "utility": utility,
            "utility_under_conflict": utility_under_conflict,
            "fairness_score": fairness_score,
        },
        "evaluation_lattice": {
            "coverage_score": concern_coverage,
            "weighted_coverage_score": weighted_coverage,
            "specificity_score": requirement_specificity,
            "traceability_score": traceability_completeness,
            "conflict_resolution_score": conflict_preservation,
            "ambiguity_penalty": requirement_ambiguity,
            "hallucination_penalty": hallucination_rate,
        },
        "uncovered_concerns": uncovered,
        "hallucinated_requirements": hallucinated,
        "conflict_summaries": conflict_summaries,
        "traceability_inputs": traceability,
        "stakeholder_scores": stakeholder_scores,
        "rubric": rubric,
        "timestamp": _utc_now_iso(),
    }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _collect_requirements(artifact: dict) -> list[dict]:
    requirements: list[dict] = []
    for item in artifact.get("functional_requirements", []):
        requirements.append({"id": item.get("id", ""), "text": item.get("description", "")})
    for item in artifact.get("non_functional_requirements", []):
        requirements.append({"id": item.get("id", ""), "text": item.get("description", "")})
    for item in artifact.get("user_stories", []):
        requirements.append({"id": item.get("id", ""), "text": item.get("description", "")})
    for item in artifact.get("acceptance_criteria", []):
        text = " ".join(
            str(part)
            for part in [item.get("given"), item.get("when"), item.get("then")]
            if part
        )
        requirements.append({"id": item.get("id", ""), "text": text})
    return requirements


def _build_concern_map(stakeholder_inputs: list[dict]) -> list[dict]:
    concerns: list[dict] = []
    for stakeholder in stakeholder_inputs:
        name = str(stakeholder.get("stakeholder", ""))
        weighted = stakeholder.get("weighted_concerns", []) or []
        weighted_lookup = {
            str(item.get("concern")): float(item.get("weight", 0))
            for item in weighted
            if isinstance(item, dict)
        }
        for concern in stakeholder.get("concerns", []) or []:
            concerns.append(
                {
                    "stakeholder": name,
                    "concern": str(concern),
                    "weight": weighted_lookup.get(str(concern), 0.0),
                }
            )
        for item in weighted:
            if not isinstance(item, dict):
                continue
            concern = str(item.get("concern", ""))
            if not concern:
                continue
            if not any(
                c["stakeholder"] == name and c["concern"] == concern for c in concerns
            ):
                concerns.append(
                    {
                        "stakeholder": name,
                        "concern": concern,
                        "weight": float(item.get("weight", 0)),
                    }
                )
    return concerns


def _compute_concern_coverage(
    concern_map: list[dict],
    requirement_texts: dict[str, str],
    rubric: dict,
) -> tuple[float, float, list[dict]]:
    covered = 0
    total = len(concern_map)
    weighted_total = 0.0
    weighted_covered = 0.0
    uncovered: list[dict] = []
    for concern in concern_map:
        weight = max(float(concern.get("weight", 0.0)), 0.0)
        weighted_total += weight
        matches = _match_text_to_requirements(
            concern.get("concern", ""),
            requirement_texts,
            rubric,
        )
        if matches:
            covered += 1
            weighted_covered += weight
        else:
            uncovered.append(concern)

    concern_coverage = covered / total if total else 0.0
    weighted_coverage = weighted_covered / weighted_total if weighted_total else 0.0
    return concern_coverage, weighted_coverage, uncovered


def _compute_traceability_completeness(
    requirement_texts: dict[str, str],
    concern_map: list[dict],
    rubric: dict,
) -> float:
    total = len(requirement_texts)
    if not total:
        return 0.0
    linked = 0
    concerns = [c.get("concern", "") for c in concern_map]
    for req_id, text in requirement_texts.items():
        if _match_any_concern(text, concerns, rubric):
            linked += 1
    return linked / total


def _compute_hallucination_rate(
    requirement_texts: dict[str, str],
    stakeholder_inputs: list[dict],
    rubric: dict,
) -> tuple[float, list[str]]:
    total = len(requirement_texts)
    if not total:
        return 0.0, []
    stakeholder_phrases: list[str] = []
    for stakeholder in stakeholder_inputs:
        for key in ["goals", "needs", "concerns", "constraints", "tradeoffs"]:
            stakeholder_phrases.extend(stakeholder.get(key, []) or [])
    hallucinated: list[str] = []
    for req_id, text in requirement_texts.items():
        if not _match_any_concern(text, stakeholder_phrases, rubric):
            hallucinated.append(req_id)
    return len(hallucinated) / total, hallucinated


def _compute_requirement_specificity(requirements: list[dict], rubric: dict) -> float:
    if not requirements:
        return 0.0
    scores = []
    for req in requirements:
        text = req.get("text", "")
        score = 0.0
        if _has_measurement(text):
            score += 0.5
        if _has_actor_and_action(text):
            score += 0.5
        scores.append(score)
    return sum(scores) / len(scores)


def _compute_acceptance_testability(criteria: Iterable[dict], rubric: dict) -> float:
    criteria = list(criteria)
    if not criteria:
        return 0.0
    passed = 0
    for ac in criteria:
        given = str(ac.get("given", ""))
        when = str(ac.get("when", ""))
        then = str(ac.get("then", ""))
        text = " ".join([given, when, then]).strip()
        if not (given and when and then):
            continue
        if _contains_ambiguity(text, rubric):
            continue
        if _has_measurement(text) or _has_observable_outcome(text):
            passed += 1
    return passed / len(criteria)


def _compute_requirement_ambiguity(requirements: list[dict], rubric: dict) -> float:
    if not requirements:
        return 0.0
    ambiguous = 0
    for req in requirements:
        if _contains_ambiguity(req.get("text", ""), rubric):
            ambiguous += 1
    return ambiguous / len(requirements)


def _compute_conflict_preservation(
    stakeholder_inputs: list[dict],
    requirement_texts: dict[str, str],
) -> tuple[float, list[dict]]:
    conflicts = _conflict_definitions()
    if not conflicts:
        return 1.0, []
    summaries: list[dict] = []
    resolved = 0
    for conflict in conflicts:
        left_present = _match_any_keyword(requirement_texts, conflict["left_keywords"])
        right_present = _match_any_keyword(requirement_texts, conflict["right_keywords"])
        tradeoff_present = _match_any_keyword(requirement_texts, conflict["tradeoff_keywords"])

        if left_present and right_present and tradeoff_present:
            status = "explicitly_resolved"
            resolved += 1
        elif left_present and right_present:
            status = "silently_merged"
        else:
            status = "ignored"
        summaries.append(
            {
                "conflict": conflict["name"],
                "status": status,
            }
        )
    preservation = resolved / len(conflicts)
    return preservation, summaries


def _compute_stakeholder_satisfaction(
    concern_map: list[dict],
    requirement_texts: dict[str, str],
    stakeholder_importance: dict[str, float],
    rubric: dict,
) -> list[dict]:
    by_stakeholder: dict[str, list[dict]] = {}
    for concern in concern_map:
        by_stakeholder.setdefault(concern["stakeholder"], []).append(concern)

    results: list[dict] = []
    for stakeholder, concerns in by_stakeholder.items():
        total_weight = sum(max(float(c.get("weight", 0.0)), 0.0) for c in concerns)
        covered_weight = 0.0
        for concern in concerns:
            matches = _match_text_to_requirements(
                concern.get("concern", ""),
                requirement_texts,
                rubric,
            )
            if matches:
                covered_weight += max(float(concern.get("weight", 0.0)), 0.0)
        satisfaction = covered_weight / total_weight if total_weight else 0.0
        importance = float(stakeholder_importance.get(stakeholder, 1.0))
        results.append(
            {
                "stakeholder": stakeholder,
                "satisfaction": satisfaction,
                "importance": importance,
            }
        )
    return results


def _compute_per_concern_matrix(
    concern_map: list[dict],
    requirement_texts: dict[str, str],
    rubric: dict,
) -> list[dict]:
    matrix: list[dict] = []
    for concern in concern_map:
        matches = _match_text_to_requirements(
            concern.get("concern", ""),
            requirement_texts,
            rubric,
        )
        if not matches:
            status = "unsatisfied"
            score = 0.0
        else:
            best_specificity = 0.0
            for req_id in matches:
                text = requirement_texts.get(req_id, "")
                specificity = 0.0
                if _has_measurement(text):
                    specificity += 0.5
                if _has_actor_and_action(text):
                    specificity += 0.5
                best_specificity = max(best_specificity, specificity)
            if best_specificity >= rubric["thresholds"]["specificity_min"]:
                status = "satisfied"
                score = 1.0
            else:
                status = "partially_satisfied"
                score = 0.5

        matrix.append(
            {
                "stakeholder": concern.get("stakeholder", ""),
                "concern": concern.get("concern", ""),
                "weight": float(concern.get("weight", 0.0)),
                "status": status,
                "score": score,
            }
        )
    return matrix


def _compute_utility_metrics(stakeholder_scores: list[dict]) -> tuple[float, float, float, float]:
    if not stakeholder_scores:
        return 0.0, 0.0, 0.0, 0.0
    utility = sum(item["satisfaction"] * item["importance"] for item in stakeholder_scores)
    total_importance = sum(item["importance"] for item in stakeholder_scores) or 1.0
    utility /= total_importance

    sats = [item["satisfaction"] for item in stakeholder_scores]
    mean = sum(sats) / len(sats)
    variance = sum((val - mean) ** 2 for val in sats) / len(sats)
    min_satisfaction = min(sats)
    fairness_score = 1 - min(variance, 1.0)
    return utility, fairness_score, variance, min_satisfaction


def _match_text_to_requirements(
    text: str,
    requirement_texts: dict[str, str],
    rubric: dict,
) -> list[str]:
    tokens = _tokenize(text)
    matches: list[str] = []
    for req_id, req_text in requirement_texts.items():
        if _token_overlap(tokens, _tokenize(req_text), rubric["thresholds"]["token_overlap"]):
            matches.append(req_id)
    return matches


def _match_any_concern(text: str, concerns: Iterable[str], rubric: dict) -> bool:
    tokens = _tokenize(text)
    for concern in concerns:
        if _token_overlap(tokens, _tokenize(str(concern)), rubric["thresholds"]["token_overlap"]):
            return True
    return False


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    stopwords = {
        "i",
        "oraz",
        "oraz",
        "dla",
        "z",
        "na",
        "do",
        "w",
        "we",
        "ze",
        "jak",
        "aby",
        "sie",
        "nie",
        "tak",
        "to",
        "jest",
        "byc",
        "sa",
        "ma",
        "miec",
        "mozna",
        "mozliwe",
        "system",
        "uzytkownik",
    }
    return {token for token in tokens if token not in stopwords and len(token) > 2}


def _token_overlap(tokens_a: set[str], tokens_b: set[str], threshold: int) -> bool:
    return len(tokens_a.intersection(tokens_b)) >= threshold


def _has_measurement(text: str) -> bool:
    return bool(re.search(r"\b\d+([\.,]\d+)?\b", text)) or any(
        term in text.lower()
        for term in ["sek", "ms", "%", "min", "godz", "dni", "h", "s"]
    )


def _has_actor_and_action(text: str) -> bool:
    actor_terms = ["uzytkownik", "system", "administrator", "specjalista", "klient"]
    action_terms = ["moze", "musi", "tworzy", "rezerwuje", "anuluje", "zatwierdza", "wysyla"]
    lower = text.lower()
    return any(term in lower for term in actor_terms) and any(
        term in lower for term in action_terms
    )


def _has_observable_outcome(text: str) -> bool:
    lower = text.lower()
    return any(
        term in lower
        for term in ["wyswietl", "zapis", "log", "powiadom", "status", "blad"]
    )


def _contains_ambiguity(text: str, rubric: dict) -> bool:
    lower = text.lower()
    if any(term in lower for term in rubric["ambiguity_terms"]):
        if not _has_measurement(lower):
            return True
    return False


def _match_any_keyword(requirement_texts: dict[str, str], keywords: list[str]) -> bool:
    lower_keywords = [kw.lower() for kw in keywords]
    for text in requirement_texts.values():
        lower = text.lower()
        if any(kw in lower for kw in lower_keywords):
            return True
    return False


def _conflict_definitions() -> list[dict]:
    return [
        {
            "name": "security_vs_ux_friction",
            "left_keywords": ["mfa", "dwuetap", "silna polityka hasel"],
            "right_keywords": ["bez tarcia", "minimalna liczba krokow", "szybki onboarding"],
            "tradeoff_keywords": ["wyjatek", "opcjonal", "tryb", "kompromis"],
        },
        {
            "name": "business_speed_vs_qa_rigor",
            "left_keywords": ["szybki release", "time-to-market"],
            "right_keywords": ["testy regresji", "kryteria akceptacji"],
            "tradeoff_keywords": ["etap", "faza", "kompromis", "pilota"],
        },
        {
            "name": "logging_cost_vs_audit",
            "left_keywords": ["niski koszt", "minimalny zakres"],
            "right_keywords": ["logi audytowe", "retencja logow"],
            "tradeoff_keywords": ["retencja", "okres", "kompromis", "tier"],
        },
    ]
