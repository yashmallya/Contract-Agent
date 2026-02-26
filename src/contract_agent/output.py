"""Output formatting utilities

Produce structured JSON from analysis results.
"""

import json
from typing import Dict, Any


def _normalize_liability(liability: Any) -> Dict[str, Any]:
    normalized = dict(liability) if isinstance(liability, dict) else {"clause_text": str(liability)}
    normalized.setdefault("severity", "Low")
    normalized.setdefault("reason", normalized.get("reason") or "")
    normalized.setdefault("recommendation", normalized.get("recommendation") or "")
    normalized.setdefault(
        "risk_type", normalized.get("risk_type") or normalized.get("obligation_type") or "Liability"
    )
    normalized["clause_text"] = normalized.get("clause_text") or ""
    normalized.setdefault("resolution", normalized.get("resolution") or normalized.get("recommendation") or "")
    normalized.setdefault("plain_english", normalized.get("plain_english") or normalized.get("reason") or "")
    return normalized


def _normalize_red_flag(red_flag: Any) -> Dict[str, Any]:
    normalized = dict(red_flag) if isinstance(red_flag, dict) else {"description": str(red_flag)}
    normalized.setdefault("category", normalized.get("category") or "Lease Risk")
    normalized.setdefault("description", normalized.get("description") or "")
    normalized.setdefault("severity", normalized.get("severity") or "Moderate")
    normalized.setdefault("why_problematic", normalized.get("why_problematic") or "")
    normalized.setdefault("suggested_fix", normalized.get("suggested_fix") or "")
    normalized.setdefault("resolution", normalized.get("resolution") or normalized.get("suggested_fix") or "")
    normalized.setdefault(
        "plain_english", normalized.get("plain_english") or normalized.get("why_problematic") or ""
    )
    return normalized


def format_output(summary: str, liabilities: list, red_flags: list, overall_score: int, risk_level: str) -> str:
    # Accept that `red_flags` may be a dict with metrics from the detector.
    metrics = red_flags if isinstance(red_flags, dict) else {"red_flags": red_flags}

    normalized_liabilities = []
    for liability in liabilities or []:
        normalized_liabilities.append(_normalize_liability(liability))

    normalized_red_flags = []
    for red_flag in metrics.get("red_flags", []):
        normalized_red_flags.append(_normalize_red_flag(red_flag))

    data = {
        "contract_summary": summary,
        "overall_risk_score": overall_score,
        "risk_level": risk_level,
        "liability_clauses": normalized_liabilities,
        "red_flags": normalized_red_flags,
        "asymmetry_ratio": metrics.get("asymmetry_ratio"),
        "uncapped_parties": metrics.get("uncapped_parties", []),
        "illusory_cap": metrics.get("illusory_cap", False),
        "illusory_reasons": metrics.get("illusory_reasons", []),
        "highest_indemnity_tier": metrics.get("highest_indemnity_tier", 0),
    }
    return json.dumps(data, indent=2)
