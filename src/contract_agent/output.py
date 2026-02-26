"""Output formatting utilities

Produce structured JSON from analysis results.
"""

import json
from typing import Dict, Any


def format_output(summary: str, liabilities: list, red_flags: list, overall_score: int, risk_level: str) -> str:
    data = {
        "contract_summary": summary,
        "overall_risk_score": overall_score,
        "risk_level": risk_level,
        "liability_clauses": liabilities,
        "red_flags": red_flags,
    }
    return json.dumps(data, indent=2)
