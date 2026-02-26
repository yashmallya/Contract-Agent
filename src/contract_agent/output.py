"""Output formatting utilities

Produce structured JSON from analysis results.
"""

import json
from typing import Dict, Any


def format_output(summary: str, liabilities: list, red_flags: list, overall_score: int, risk_level: str) -> str:
    # Accept that `red_flags` may be a dict with metrics from new detector
    metrics = red_flags if isinstance(red_flags, dict) else {'red_flags': red_flags}
    data = {
        "contract_summary": summary,
        "overall_risk_score": overall_score,
        "risk_level": risk_level,
        "liability_clauses": liabilities,
        "red_flags": metrics.get('red_flags', []),
        "asymmetry_ratio": metrics.get('asymmetry_ratio'),
        "uncapped_parties": metrics.get('uncapped_parties', []),
        "illusory_cap": metrics.get('illusory_cap', False),
        "illusory_reasons": metrics.get('illusory_reasons', []),
        "highest_indemnity_tier": metrics.get('highest_indemnity_tier', 0)
    }
    return json.dumps(data, indent=2)
