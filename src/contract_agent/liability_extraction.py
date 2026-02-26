"""Liability Extraction Agent

Operates on the obligation graph produced by `structuring` to extract
liability-related objects and normalize fields for downstream analysis.
"""

from typing import Dict, List


def extract_liabilities(obligation_graph: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Filter obligation graph for liability-relevant entries and normalize.

    Returns a list of dicts with keys: clause_text, obligated_party, benefiting_party,
    obligation_type, financial_exposure, cap, exceptions.
    """
    liabilities: List[Dict[str, object]] = []
    for obligation in obligation_graph:
        obligation_type = obligation.get("obligation_type") or ""
        clause_text = obligation.get("clause_text") or ""
        is_liability_related = (
            obligation_type in ("indemnity", "liability", "payment")
            or "liab" in clause_text.lower()
            or "indemn" in clause_text.lower()
        )
        if not is_liability_related:
            continue

        liabilities.append(
            {
                "clause_text": clause_text,
                "obligated_party": obligation.get("obligated_party"),
                "benefiting_party": obligation.get("benefiting_party"),
                "obligation_type": obligation_type or "unknown",
                "financial_exposure": obligation.get("financial_exposure"),
                "cap": obligation.get("cap"),
                "exceptions": obligation.get("exceptions") or [],
            }
        )
    return liabilities
