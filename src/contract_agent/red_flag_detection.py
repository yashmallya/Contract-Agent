"""Red Flag Detection Agent

Implements the improved rulebook and interaction detection (layers 2-4).
"""

from typing import Any, Dict, List, Tuple
import re

TERMINATION_PENALTY_PATTERN = re.compile(r"termination.*?(?:penalt(?:y|ies)|fee).*?(?:([0-9]{1,3})%)")
AUTO_RENEW_NOTICE_PATTERN = re.compile(r"auto-?renew.*?notice.*?(?:([0-9]{1,3})\s*days?)")
CONTROL_TOPICS = ["defense", "settlement", "assignment", "price revision", "termination", "arbitrat"]
ILLUSORY_CAP_KEYWORDS = [
    "data breach",
    "data loss",
    "regulat",
    "third-party",
    "third party",
    "ip infringe",
    "intellectual property",
    "indemnif",
]


def classify_indemnity_tier(clause_text: str) -> int:
    text_lower = clause_text.lower()
    if "uncap" in text_lower or "no cap" in text_lower or "no limitation" in text_lower:
        return 5
    if "gross negligence" in text_lower or "willful misconduct" in text_lower:
        return 4
    if "other party negligence" in text_lower or "negligence of" in text_lower:
        return 3
    if "third party" in text_lower and "claim" in text_lower:
        return 1
    if "any and all" in text_lower or "broad" in text_lower:
        return 2
    return 1


def compute_exposure_estimate(liabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Estimate simple exposure buckets by party."""
    totals = {}
    uncapped = {}
    for liability in liabilities:
        party = liability.get("obligated_party") or "unknown"
        cap = liability.get("cap")
        exposure = 0
        if liability.get("financial_exposure"):
            try:
                exposure = float(liability.get("financial_exposure"))
            except Exception:
                exposure = 0

        if cap:
            try:
                totals[party] = totals.get(party, 0) + float(cap)
            except Exception:
                totals[party] = totals.get(party, 0) + exposure
        else:
            uncapped[party] = True

    return {"totals": totals, "uncapped": uncapped}


def detect_illusory_cap(liabilities: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Detect if caps are undermined by carve-outs/exceptions."""
    reasons = []
    cap_exists = any(liability.get("cap") for liability in liabilities)
    if not cap_exists:
        return (False, [])

    for liability in liabilities:
        exceptions_text = " ".join(liability.get("exceptions") or "").lower()
        for keyword in ILLUSORY_CAP_KEYWORDS:
            if keyword in exceptions_text:
                reasons.append(
                    f"Cap carve-out mentions '{keyword}' in clause: {liability.get('clause_text')[:120]}"
                )

    return (len(reasons) > 0, reasons)


def _append_indemnity_flags(liabilities: List[Dict[str, Any]], red_flags: List[Dict[str, Any]]) -> int:
    highest_indemnity_tier = 0
    for liability in liabilities:
        tier = classify_indemnity_tier(liability.get("clause_text", ""))
        if tier >= 3:
            severity = "High" if tier == 3 else "Critical"
            red_flags.append(
                {
                    "category": "Indemnity",
                    "description": liability.get("clause_text"),
                    "why_problematic": f"Indemnity tier {tier}",
                    "suggested_fix": "Narrow scope; add cap",
                    "severity": severity,
                }
            )
        highest_indemnity_tier = max(highest_indemnity_tier, tier)
    return highest_indemnity_tier


def _compute_asymmetry(
    liabilities: List[Dict[str, Any]], totals: Dict[str, float], uncapped: Dict[str, bool]
) -> Tuple[Any, Any]:
    parties = list(set([liability.get("obligated_party") or "unknown" for liability in liabilities]))
    asymmetry_ratio = None
    asymmetry_flag = None

    a_val = totals.get(parties[0], 0) if parties else 0
    b_val = totals.get(parties[1], 0) if len(parties) > 1 else 0
    try:
        if parties and len(parties) > 1:
            a_val = totals.get(parties[0], 0) or 0
            b_val = totals.get(parties[1], 0) or 0
            if b_val == 0 and uncapped.get(parties[0]):
                asymmetry_ratio = float("inf")
            elif b_val == 0:
                asymmetry_ratio = float("inf") if uncapped.get(parties[0]) else (a_val and float("inf"))
            else:
                asymmetry_ratio = (a_val or 0) / (b_val or 1)

            if asymmetry_ratio and asymmetry_ratio > 5:
                asymmetry_flag = "Critical"
            elif asymmetry_ratio and asymmetry_ratio > 3:
                asymmetry_flag = "High"
    except Exception:
        asymmetry_ratio = None

    return asymmetry_ratio, asymmetry_flag


def _detect_termination_risk(obligation_graph: List[Dict[str, Any]]) -> Tuple[int, bool, Any, int]:
    termination_count = 0
    acceleration = False
    auto_renewal_notice = None
    termination_penalty_pct = 0

    for obligation in obligation_graph:
        clause_text = obligation.get("clause_text", "").lower()
        if "termination for convenience" in clause_text or "termination for convenience" in clause_text:
            termination_count += 1
        if "accelerat" in clause_text:
            acceleration = True

        penalty_match = TERMINATION_PENALTY_PATTERN.search(clause_text)
        if penalty_match:
            try:
                termination_penalty_pct = max(termination_penalty_pct, int(penalty_match.group(1)))
            except Exception:
                pass

        notice_match = AUTO_RENEW_NOTICE_PATTERN.search(clause_text)
        if notice_match:
            auto_renewal_notice = int(notice_match.group(1))

    return termination_count, acceleration, auto_renewal_notice, termination_penalty_pct


def detect_red_flags(
    liabilities: List[Dict[str, Any]], obligation_graph: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Return red flags and supporting risk metrics."""
    red_flags = []

    highest_indemnity_tier = _append_indemnity_flags(liabilities, red_flags)
    illusory, reasons = detect_illusory_cap(liabilities)
    if illusory:
        red_flags.append(
            {
                "category": "Liability Cap",
                "description": "Liability cap undermined by carve-outs",
                "why_problematic": "; ".join(reasons),
                "suggested_fix": "Remove carve-outs or include them in cap",
                "severity": "Critical",
            }
        )

    exp = compute_exposure_estimate(liabilities)
    totals = exp.get("totals", {})
    uncapped = exp.get("uncapped", {})
    asym_ratio, asym_flag = _compute_asymmetry(liabilities, totals, uncapped)

    termination_count, acceleration, auto_renewal_notice, termination_penalty_pct = _detect_termination_risk(
        obligation_graph
    )
    if (
        (termination_count >= 1 and acceleration)
        or (termination_penalty_pct > 100)
        or (auto_renewal_notice and auto_renewal_notice > 60)
    ):
        red_flags.append(
            {
                "category": "Termination",
                "description": "Termination financial trap detected",
                "why_problematic": (
                    f"acceleration={acceleration}, "
                    f"penalty_pct={termination_penalty_pct}, "
                    f"auto_renewal_notice={auto_renewal_notice}"
                ),
                "suggested_fix": "Cap penalties; extend cure periods",
                "severity": (
                    "Critical"
                    if termination_penalty_pct > 100 or (termination_count >= 1 and acceleration)
                    else "High"
                ),
            }
        )

    compound_risk = False
    for obligation in obligation_graph:
        clause_text = obligation.get("clause_text", "").lower()
        if "interest" in clause_text and "%" in clause_text and "compound" in clause_text:
            compound_risk = True
    if compound_risk:
        red_flags.append(
            {
                "category": "Financial",
                "description": "Compounded interest detected",
                "why_problematic": "Compounds exposure over time",
                "suggested_fix": "Limit interest rate and compounding",
                "severity": "High",
            }
        )

    for obligation in obligation_graph:
        clause_text = obligation.get("clause_text", "").lower()
        if "assign" in clause_text and ("background" in clause_text or "intellectual property" in clause_text):
            red_flags.append(
                {
                    "category": "IP",
                    "description": obligation.get("clause_text"),
                    "why_problematic": "Background IP assignment or broad rights",
                    "suggested_fix": "Limit scope and provide compensation",
                    "severity": "Critical",
                }
            )
        if "use data" in clause_text or "data for any purpose" in clause_text or "commercial" in clause_text and "data" in clause_text:
            red_flags.append(
                {
                    "category": "Data",
                    "description": obligation.get("clause_text"),
                    "why_problematic": "Unrestricted data use",
                    "suggested_fix": "Limit use and purpose",
                    "severity": "Critical",
                }
            )

    survival_multiplier = 1.0
    for obligation in obligation_graph:
        clause_text = obligation.get("clause_text", "").lower()
        if (
            ("survive" in clause_text or "survival" in clause_text or "indefinite" in clause_text)
            and ("indemn" in clause_text or "liabil" in clause_text or "confidential" in clause_text)
        ):
            survival_multiplier = max(survival_multiplier, 1.3)
            red_flags.append(
                {
                    "category": "Survival",
                    "description": obligation.get("clause_text"),
                    "why_problematic": "Indefinite survival increases perpetual exposure",
                    "suggested_fix": "Limit survival periods to reasonable years",
                    "severity": "High",
                }
            )

    for liability in liabilities:
        clause_text = liability.get("clause_text", "").lower()
        if "regulat" in clause_text and ("fine" in clause_text or "penalt" in clause_text) and (
            "indemn" in clause_text or "indemnify" in clause_text
        ):
            red_flags.append(
                {
                    "category": "Regulatory",
                    "description": liability.get("clause_text"),
                    "why_problematic": "Pass-through of regulatory fines",
                    "suggested_fix": "Remove pass-through or add cap",
                    "severity": "Critical",
                }
            )

    control_imbalance = False
    for obligation in obligation_graph:
        clause_text = obligation.get("clause_text", "").lower()
        for control_topic in CONTROL_TOPICS:
            if control_topic in clause_text and (
                "sole" in clause_text or "exclusive" in clause_text or "shall control" in clause_text
            ):
                control_imbalance = True
                red_flags.append(
                    {
                        "category": "Control",
                        "description": obligation.get("clause_text"),
                        "why_problematic": f"Control over {control_topic} by one party",
                        "suggested_fix": "Share control or require consent",
                        "severity": "High",
                    }
                )

    metrics = {
        "red_flags": red_flags,
        "asymmetry_ratio": asym_ratio,
        "asymmetry_severity": asym_flag,
        "exposure_totals": totals,
        "uncapped_parties": list(uncapped.keys()),
        "illusory_cap": illusory,
        "illusory_reasons": reasons,
        "highest_indemnity_tier": highest_indemnity_tier,
        "survival_multiplier": survival_multiplier,
        "control_imbalance": control_imbalance,
    }

    return metrics
