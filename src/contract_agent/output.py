"""Output formatting utilities

Produce structured JSON from analysis results.
"""

import json
from typing import Dict, Any


def format_output(summary: str, liabilities: list, red_flags: list, overall_score: int, risk_level: str) -> str:
    # Accept that `red_flags` may be a dict with metrics from new detector
    metrics = red_flags if isinstance(red_flags, dict) else {'red_flags': red_flags}
    # Ensure each liability clause contains UI-friendly fields expected by frontend
    normalized_liabilities = []
    for l in (liabilities or []):
        nl = dict(l) if isinstance(l, dict) else {'clause_text': str(l)}
        # Provide defaults for UI to avoid JS errors
        nl.setdefault('severity', 'Low')
        nl.setdefault('reason', nl.get('reason') or '')
        nl.setdefault('recommendation', nl.get('recommendation') or '')
        # risk_type preferred, otherwise fallback to obligation_type or generic label
        nl.setdefault('risk_type', nl.get('risk_type') or nl.get('obligation_type') or 'Liability')
        # ensure clause_text is a string
        nl['clause_text'] = nl.get('clause_text') or ''
        normalized_liabilities.append(nl)

    data = {
        "contract_summary": summary,
        "overall_risk_score": overall_score,
        "risk_level": risk_level,
        "liability_clauses": normalized_liabilities,
        "red_flags": metrics.get('red_flags', []),
        "asymmetry_ratio": metrics.get('asymmetry_ratio'),
        "uncapped_parties": metrics.get('uncapped_parties', []),
        "illusory_cap": metrics.get('illusory_cap', False),
        "illusory_reasons": metrics.get('illusory_reasons', []),
        "highest_indemnity_tier": metrics.get('highest_indemnity_tier', 0)
    }
    return json.dumps(data, indent=2)
