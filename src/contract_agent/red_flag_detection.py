"""Red Flag Detection Agent

Implements the improved rulebook and interaction detection (layers 2-4).
"""

from typing import List, Dict, Any, Tuple
import math


def classify_indemnity_tier(clause_text: str) -> int:
    t = clause_text.lower()
    # Tier detection heuristics
    if 'uncap' in t or 'no cap' in t or 'no limitation' in t:
        return 5
    if 'gross negligence' in t or 'willful misconduct' in t:
        return 4
    if 'other party negligence' in t or 'negligence of' in t:
        return 3
    if 'third party' in t and 'claim' in t:
        return 1
    if 'any and all' in t or 'broad' in t:
        return 2
    return 1


def compute_exposure_estimate(liabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Estimate simple exposure buckets by party.

    Returns totals and a flag for uncapped exposure.
    """
    totals = {}
    uncapped = {}
    for l in liabilities:
        p = l.get('obligated_party') or 'unknown'
        cap = l.get('cap')
        exposure = 0
        if l.get('financial_exposure'):
            try:
                exposure = float(l.get('financial_exposure'))
            except Exception:
                exposure = 0
        if cap:
            try:
                totals[p] = totals.get(p, 0) + float(cap)
            except Exception:
                totals[p] = totals.get(p, 0) + exposure
        else:
            # no cap: mark as uncapped
            uncapped[p] = True

    return {'totals': totals, 'uncapped': uncapped}


def detect_illusory_cap(liabilities: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Detect if caps are undermined by carve-outs/exceptions.

    Returns (is_illusory, reasons)
    """
    reasons = []
    cap_exists = any(l.get('cap') for l in liabilities)
    if not cap_exists:
        return (False, [])

    for l in liabilities:
        ex = ' '.join(l.get('exceptions') or [])
        low = ex.lower()
        # High risk carve-outs
        for keyword in ['data breach', 'data loss', 'regulat', 'third-party', 'third party', 'ip infringe', 'intellectual property', 'indemnif']:
            if keyword in low:
                reasons.append(f"Cap carve-out mentions '{keyword}' in clause: {l.get('clause_text')[:120]}")
    return (len(reasons) > 0, reasons)


def detect_red_flags(liabilities: List[Dict[str, Any]], obligation_graph: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return a dict with red_flags list and metrics like asymmetry_ratio etc."""
    red_flags = []

    # Indemnity tiers
    highest_indemnity_tier = 0
    for l in liabilities:
        t = classify_indemnity_tier(l.get('clause_text', ''))
        if t >= 3:
            sev = 'High' if t == 3 else 'Critical'
            red_flags.append({'category': 'Indemnity', 'description': l.get('clause_text'), 'why_problematic': f'Indemnity tier {t}', 'suggested_fix': 'Narrow scope; add cap', 'severity': sev})
        highest_indemnity_tier = max(highest_indemnity_tier, t)

    # Illusory cap detection
    illusory, reasons = detect_illusory_cap(liabilities)
    if illusory:
        red_flags.append({'category': 'Liability Cap', 'description': 'Liability cap undermined by carve-outs', 'why_problematic': '; '.join(reasons), 'suggested_fix': 'Remove carve-outs or include them in cap', 'severity': 'Critical'})

    # Compute exposure estimates and asymmetry
    exp = compute_exposure_estimate(liabilities)
    totals = exp.get('totals', {})
    uncapped = exp.get('uncapped', {})

    # compute asymmetry ratio
    parties = list(set([l.get('obligated_party') or 'unknown' for l in liabilities]))
    a_val = totals.get(parties[0], 0) if parties else 0
    b_val = totals.get(parties[1], 0) if len(parties) > 1 else 0
    asym_ratio = None
    asym_flag = None
    try:
        if parties and len(parties) > 1:
            a_val = totals.get(parties[0], 0) or 0
            b_val = totals.get(parties[1], 0) or 0
            if b_val == 0 and uncapped.get(parties[0]):
                asym_ratio = float('inf')
            elif b_val == 0:
                asym_ratio = float('inf') if uncapped.get(parties[0]) else (a_val and float('inf'))
            else:
                asym_ratio = (a_val or 0) / (b_val or 1)
            if asym_ratio and asym_ratio > 5:
                asym_flag = 'Critical'
            elif asym_ratio and asym_ratio > 3:
                asym_flag = 'High'
    except Exception:
        asym_ratio = None

    # Interaction checks: termination traps and compounded exposure
    # Termination detection heuristics
    termination_count = 0
    acceleration = False
    auto_renewal_notice = None
    termination_penalty_pct = 0
    for o in obligation_graph:
        t = o.get('clause_text', '').lower()
        if 'termination for convenience' in t or 'termination for convenience' in t:
            termination_count += 1
        if 'accelerat' in t:
            acceleration = True
        # detect penalty percent
        import re as _re
        m = _re.search(r'termination.*?(?:penalt(?:y|ies)|fee).*?(?:([0-9]{1,3})%)', t)
        if m:
            try:
                termination_penalty_pct = max(termination_penalty_pct, int(m.group(1)))
            except Exception:
                pass
        # auto-renewal window
        m2 = _re.search(r'auto-?renew.*?notice.*?(?:([0-9]{1,3})\s*days?)', t)
        if m2:
            auto_renewal_notice = int(m2.group(1))

    if (termination_count >= 1 and acceleration) or (termination_penalty_pct > 100) or (auto_renewal_notice and auto_renewal_notice > 60):
        red_flags.append({'category': 'Termination', 'description': 'Termination financial trap detected', 'why_problematic': f'acceleration={acceleration}, penalty_pct={termination_penalty_pct}, auto_renewal_notice={auto_renewal_notice}', 'suggested_fix': 'Cap penalties; extend cure periods', 'severity': 'Critical' if termination_penalty_pct>100 or (termination_count>=1 and acceleration) else 'High'})

    # Compounded financial exposure
    compound_risk = False
    for o in obligation_graph:
        t = o.get('clause_text', '').lower()
        if 'interest' in t and '%' in t and 'compound' in t:
            compound_risk = True
    if compound_risk:
        red_flags.append({'category': 'Financial', 'description': 'Compounded interest detected', 'why_problematic': 'Compounds exposure over time', 'suggested_fix': 'Limit interest rate and compounding', 'severity': 'High'})

    # IP & data exploitation
    for o in obligation_graph:
        t = o.get('clause_text', '').lower()
        if 'assign' in t and ('background' in t or 'intellectual property' in t):
            red_flags.append({'category': 'IP', 'description': o.get('clause_text'), 'why_problematic': 'Background IP assignment or broad rights', 'suggested_fix': 'Limit scope and provide compensation', 'severity': 'Critical'})
        if 'use data' in t or 'data for any purpose' in t or 'commercial' in t and 'data' in t:
            red_flags.append({'category': 'Data', 'description': o.get('clause_text'), 'why_problematic': 'Unrestricted data use', 'suggested_fix': 'Limit use and purpose', 'severity': 'Critical'})

    # survival amplification
    survival_multiplier = 1.0
    for o in obligation_graph:
        t = o.get('clause_text', '').lower()
        if ('survive' in t or 'survival' in t or 'indefinite' in t) and ('indemn' in t or 'liabil' in t or 'confidential' in t):
            survival_multiplier = max(survival_multiplier, 1.3)
            red_flags.append({'category': 'Survival', 'description': o.get('clause_text'), 'why_problematic': 'Indefinite survival increases perpetual exposure', 'suggested_fix': 'Limit survival periods to reasonable years', 'severity': 'High'})

    # regulatory fine pass-through
    for l in liabilities:
        t = l.get('clause_text', '').lower()
        if 'regulat' in t and ('fine' in t or 'penalt' in t) and ('indemn' in t or 'indemnify' in t):
            red_flags.append({'category': 'Regulatory', 'description': l.get('clause_text'), 'why_problematic': 'Pass-through of regulatory fines', 'suggested_fix': 'Remove pass-through or add cap', 'severity': 'Critical'})

    # control imbalance
    control_imbalance = False
    for o in obligation_graph:
        t = o.get('clause_text', '').lower()
        for ctrl in ['defense', 'settlement', 'assignment', 'price revision', 'termination', 'arbitrat']:
            if ctrl in t and ('sole' in t or 'exclusive' in t or 'shall control' in t):
                control_imbalance = True
                red_flags.append({'category': 'Control', 'description': o.get('clause_text'), 'why_problematic': f'Control over {ctrl} by one party', 'suggested_fix': 'Share control or require consent', 'severity': 'High'})

    metrics = {
        'red_flags': red_flags,
        'asymmetry_ratio': asym_ratio,
        'asymmetry_severity': asym_flag,
        'exposure_totals': totals,
        'uncapped_parties': list(uncapped.keys()),
        'illusory_cap': illusory,
        'illusory_reasons': reasons,
        'highest_indemnity_tier': highest_indemnity_tier,
        'survival_multiplier': survival_multiplier,
        'control_imbalance': control_imbalance
    }

    return metrics

