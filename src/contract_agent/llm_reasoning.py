"""Mandatory LLM reasoning layer for lease vetting output (Gemini)."""

import json
import os
from typing import Any, Dict, List

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover - optional dependency fallback
    genai = None
    types = None

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
DEFAULT_THINKING_BUDGET = int(os.environ.get("GEMINI_THINKING_BUDGET", "1024"))
MAX_TEXT_CHARS = int(os.environ.get("GEMINI_MAX_TEXT_CHARS", "30000"))

REQUIRED_TOP_LEVEL_KEYS = [
    "contract_summary",
    "overall_risk_score",
    "risk_level",
    "liability_clauses",
    "red_flags",
    "asymmetry_ratio",
    "uncapped_parties",
    "illusory_cap",
    "illusory_reasons",
    "highest_indemnity_tier",
]


class LLMReasoningError(RuntimeError):
    """Raised when Gemini reasoning cannot be completed."""


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return fallback


def _extract_json_block(text: str) -> Dict[str, Any]:
    candidate = (text or "").strip()
    if not candidate:
        raise LLMReasoningError("Gemini returned an empty response.")

    if candidate.startswith("```"):
        lines = [line for line in candidate.splitlines() if not line.strip().startswith("```")]
        candidate = "\n".join(lines).strip()

    try:
        return json.loads(candidate)
    except Exception:
        pass

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(candidate[start : end + 1])
        except Exception as exc:
            raise LLMReasoningError(f"Gemini returned invalid JSON: {exc}") from exc

    raise LLMReasoningError("Gemini response did not contain a JSON object.")


def _build_prompt(contract_text: str, base_result: Dict[str, Any]) -> str:
    schema_hint = {
        "contract_summary": "string",
        "overall_risk_score": "number",
        "risk_level": "Low|Moderate|High|Critical Structural Risk",
        "liability_clauses": [
            {
                "clause_text": "string",
                "risk_type": "string",
                "severity": "Low|Moderate|High|Critical",
                "reason": "plain english meaning",
                "recommendation": "actionable fix",
                "resolution": "actionable fix",
            }
        ],
        "red_flags": [
            {
                "category": "string",
                "description": "string",
                "severity": "Low|Moderate|High|Critical",
                "why_problematic": "plain english meaning",
                "suggested_fix": "actionable fix",
                "resolution": "actionable fix",
            }
        ],
        "asymmetry_ratio": "number|null",
        "uncapped_parties": ["string"],
        "illusory_cap": "boolean",
        "illusory_reasons": ["string"],
        "highest_indemnity_tier": "number",
    }

    trimmed_contract = contract_text[:MAX_TEXT_CHARS]
    return (
        "You are a senior commercial lease-risk analyst. "
        "Produce final lease vetting output in plain English for a non-lawyer. "
        "Return only valid JSON, no markdown, and keep the exact top-level keys requested.\n"
        + json.dumps(schema_hint)
        + "\n\nLease text:\n"
        + trimmed_contract
        + "\n\nDraft analysis to refine:\n"
        + json.dumps(base_result)
    )


def _validate_and_normalize_output(candidate: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(candidate, dict):
        raise LLMReasoningError("Gemini output is not a JSON object.")

    missing = [key for key in REQUIRED_TOP_LEVEL_KEYS if key not in candidate]
    if missing:
        raise LLMReasoningError(f"Gemini output missing required keys: {', '.join(missing)}")

    output: Dict[str, Any] = {
        "contract_summary": str(candidate.get("contract_summary") or ""),
        "overall_risk_score": _safe_int(candidate.get("overall_risk_score"), 0),
        "risk_level": str(candidate.get("risk_level") or "Low"),
        "asymmetry_ratio": candidate.get("asymmetry_ratio"),
        "uncapped_parties": candidate.get("uncapped_parties") if isinstance(candidate.get("uncapped_parties"), list) else [],
        "illusory_cap": bool(candidate.get("illusory_cap")),
        "illusory_reasons": candidate.get("illusory_reasons") if isinstance(candidate.get("illusory_reasons"), list) else [],
        "highest_indemnity_tier": _safe_int(candidate.get("highest_indemnity_tier"), 0),
    }

    liabilities = candidate.get("liability_clauses")
    if not isinstance(liabilities, list):
        raise LLMReasoningError("Gemini output field 'liability_clauses' must be a list.")

    normalized_liabilities: List[Dict[str, Any]] = []
    for item in liabilities:
        if not isinstance(item, dict):
            continue
        normalized_liabilities.append(
            {
                "clause_text": str(item.get("clause_text") or ""),
                "risk_type": str(item.get("risk_type") or "Lease Liability"),
                "severity": str(item.get("severity") or "Low"),
                "reason": str(item.get("reason") or ""),
                "recommendation": str(item.get("recommendation") or ""),
                "resolution": str(item.get("resolution") or item.get("recommendation") or ""),
                "obligated_party": item.get("obligated_party"),
                "benefiting_party": item.get("benefiting_party"),
                "obligation_type": item.get("obligation_type") or "unknown",
                "financial_exposure": item.get("financial_exposure"),
                "cap": item.get("cap"),
                "exceptions": item.get("exceptions") if isinstance(item.get("exceptions"), list) else [],
            }
        )
    output["liability_clauses"] = normalized_liabilities

    red_flags = candidate.get("red_flags")
    if not isinstance(red_flags, list):
        raise LLMReasoningError("Gemini output field 'red_flags' must be a list.")

    normalized_flags: List[Dict[str, Any]] = []
    for flag in red_flags:
        if not isinstance(flag, dict):
            continue
        normalized_flags.append(
            {
                "category": str(flag.get("category") or "Lease Risk"),
                "description": str(flag.get("description") or ""),
                "severity": str(flag.get("severity") or "Moderate"),
                "why_problematic": str(flag.get("why_problematic") or ""),
                "suggested_fix": str(flag.get("suggested_fix") or ""),
                "resolution": str(flag.get("resolution") or flag.get("suggested_fix") or ""),
            }
        )
    output["red_flags"] = normalized_flags

    return output


def enhance_analysis_with_llm(contract_text: str, base_result: Dict[str, Any]) -> Dict[str, Any]:
    """Generate final analysis from Gemini.

    No fallback is used. Any Gemini issue raises `LLMReasoningError`.
    """
    if genai is None or types is None:
        raise LLMReasoningError("Gemini SDK is unavailable. Install dependency: google-genai.")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise LLMReasoningError("GEMINI_API_KEY is missing. Add it to environment variables.")

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=_build_prompt(contract_text, base_result),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                thinking_config=types.ThinkingConfig(thinking_budget=DEFAULT_THINKING_BUDGET),
                temperature=0.1,
            ),
        )
    except Exception as exc:
        raise LLMReasoningError(f"Gemini request failed: {exc}") from exc

    output_text = (getattr(response, "text", None) or "").strip()
    parsed = _extract_json_block(output_text)
    return _validate_and_normalize_output(parsed)
