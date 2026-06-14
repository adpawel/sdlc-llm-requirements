from __future__ import annotations

import re
from typing import Any


def normalize_artifact(artifact: dict) -> tuple[dict, dict]:
    normalized = {**artifact}
    report: dict[str, Any] = {
        "dedup": {},
        "canonicalization": {
            "trimmed_fields": 0,
            "collapsed_spaces": 0,
        },
    }

    normalized["functional_requirements"], report["dedup"]["functional_requirements"] = _normalize_list(
        artifact.get("functional_requirements", []), "description", report
    )
    normalized["non_functional_requirements"], report["dedup"]["non_functional_requirements"] = _normalize_list(
        artifact.get("non_functional_requirements", []), "description", report
    )
    normalized["user_stories"], report["dedup"]["user_stories"] = _normalize_list(
        artifact.get("user_stories", []), "description", report
    )
    normalized["acceptance_criteria"], report["dedup"]["acceptance_criteria"] = _normalize_ac(
        artifact.get("acceptance_criteria", []), report
    )

    return normalized, report


def _normalize_list(items: list[dict], field: str, report: dict) -> tuple[list[dict], dict]:
    seen: dict[str, str] = {}
    deduped: list[dict] = []
    duplicates: list[dict] = []

    for item in items:
        text = str(item.get(field, ""))
        canon = _canonicalize(text)
        if canon in seen:
            duplicates.append({"id": item.get("id", ""), "duplicate_of": seen[canon]})
            continue
        seen[canon] = str(item.get("id", ""))
        normalized_item = {**item, field: _clean_text(text, report)}
        deduped.append(normalized_item)

    deduped.sort(key=lambda x: str(x.get("id", "")))
    return deduped, {"duplicates": duplicates}


def _normalize_ac(items: list[dict], report: dict) -> tuple[list[dict], dict]:
    seen: dict[str, str] = {}
    deduped: list[dict] = []
    duplicates: list[dict] = []

    for item in items:
        given = _clean_text(str(item.get("given", "")), report)
        when = _clean_text(str(item.get("when", "")), report)
        then = _clean_text(str(item.get("then", "")), report)
        canon = _canonicalize(" ".join([given, when, then]))
        if canon in seen:
            duplicates.append({"id": item.get("id", ""), "duplicate_of": seen[canon]})
            continue
        seen[canon] = str(item.get("id", ""))
        normalized_item = {**item, "given": given, "when": when, "then": then}
        deduped.append(normalized_item)

    deduped.sort(key=lambda x: str(x.get("id", "")))
    return deduped, {"duplicates": duplicates}


def _clean_text(text: str, report: dict) -> str:
    original = text
    cleaned = text.strip()
    if cleaned != original:
        report["canonicalization"]["trimmed_fields"] += 1

    collapsed = re.sub(r"\s+", " ", cleaned)
    if collapsed != cleaned:
        report["canonicalization"]["collapsed_spaces"] += 1

    return collapsed


def _canonicalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return text.strip()
