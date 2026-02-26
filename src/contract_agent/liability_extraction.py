"""Liability Extraction Agent

Operates on the obligation graph produced by `structuring` to extract
liability-related objects and normalize fields for downstream analysis.
"""

from typing import List, Dict


def extract_liabilities(obligation_graph: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Filter obligation graph for liability-relevant entries and normalize.

    Returns a list of dicts with keys: clause_text, obligated_party, benefiting_party,
    obligation_type, financial_exposure, cap, exceptions.
    """
    liabilities = []
    for o in obligation_graph:
        typ = o.get('obligation_type') or ''
        text = (o.get('clause_text') or '')
        if typ in ('indemnity', 'liability', 'payment') or 'liab' in text.lower() or 'indemn' in text.lower():
            liabilities.append({
                'clause_text': text,
                'obligated_party': o.get('obligated_party'),
                'benefiting_party': o.get('benefiting_party'),
                'obligation_type': typ or 'unknown',
                'financial_exposure': o.get('financial_exposure'),
                'cap': o.get('cap'),
                'exceptions': o.get('exceptions') or []
            })
    return liabilities

