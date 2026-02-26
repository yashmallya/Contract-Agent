"""Red Flag Detection Agent.

Lease-focused red flag rules with plain-language explanations and resolutions.
"""

from typing import Any, Dict, List, Tuple
import re

DAY_PATTERN = re.compile(r"(\d{1,3})\s*day")
PERCENT_PATTERN = re.compile(r"(\d{1,3})\s*%")
ILLUSORY_CAP_KEYWORDS = (
    "gross negligence",
    "willful misconduct",
    "third party",
    "regulatory",
    "indemnif",
)


def classify_indemnity_tier(clause_text: str) -> int:
    text_lower = clause_text.lower()
    if "uncap" in text_lower or "no cap" in text_lower or "no limitation" in text_lower:
        return 5
    if "gross negligence" in text_lower or "willful misconduct" in text_lower:
        return 4
    if "other party negligence" in text_lower or "negligence of" in text_lower:
        return 3
    if "any and all" in text_lower:
        return 2
    return 1


def _add_flag(
    red_flags: List[Dict[str, Any]],
    *,
    category: str,
    description: str,
    why: str,
    fix: str,
    severity: str,
) -> None:
    red_flags.append(
        {
            "category": category,
            "description": description,
            "why_problematic": why,
            "suggested_fix": fix,
            "resolution": fix,
            "severity": severity,
        }
    )


def compute_exposure_estimate(liabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Estimate simple exposure buckets by party."""
    totals: Dict[str, float] = {}
    uncapped: Dict[str, bool] = {}
    for liability in liabilities:
        party = liability.get("obligated_party") or "unknown"
        cap = liability.get("cap")
        exposure = 0.0
        try:
            if liability.get("financial_exposure"):
                exposure = float(liability.get("financial_exposure"))
        except Exception:
            exposure = 0.0

        if cap:
            try:
                totals[party] = totals.get(party, 0.0) + float(cap)
            except Exception:
                totals[party] = totals.get(party, 0.0) + exposure
        else:
            uncapped[party] = True

    return {"totals": totals, "uncapped": uncapped}


def detect_illusory_cap(liabilities: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Detect if liability caps are weakened by broad carve-outs."""
    reasons = []
    cap_exists = any(liability.get("cap") for liability in liabilities)
    if not cap_exists:
        return False, []

    for liability in liabilities:
        exceptions_text = " ".join(liability.get("exceptions") or []).lower()
        for keyword in ILLUSORY_CAP_KEYWORDS:
            if keyword in exceptions_text:
                reasons.append(
                    f"Cap carve-out includes '{keyword}' which can reopen large uncapped claims."
                )

    return len(reasons) > 0, reasons


def _append_indemnity_flags(liabilities: List[Dict[str, Any]], red_flags: List[Dict[str, Any]]) -> int:
    highest_indemnity_tier = 0
    for liability in liabilities:
        clause_text = liability.get("clause_text", "")
        tier = classify_indemnity_tier(clause_text)
        highest_indemnity_tier = max(highest_indemnity_tier, tier)
        if tier < 3:
            continue

        severity = "High" if tier == 3 else "Critical"
        _add_flag(
            red_flags,
            category="Indemnity",
            description=clause_text,
            why="This indemnity clause is very broad and could expose the tenant to large third-party costs.",
            fix="Limit indemnity to direct damages caused by your fault and add a clear financial cap.",
            severity=severity,
        )
    return highest_indemnity_tier


def _compute_asymmetry(
    liabilities: List[Dict[str, Any]], totals: Dict[str, float], uncapped: Dict[str, bool]
) -> Tuple[Any, Any]:
    parties = list({liability.get("obligated_party") or "unknown" for liability in liabilities})
    asymmetry_ratio = None
    asymmetry_flag = None
    try:
        if len(parties) > 1:
            a_val = totals.get(parties[0], 0.0) or 0.0
            b_val = totals.get(parties[1], 0.0) or 0.0
            if b_val == 0 and uncapped.get(parties[0]):
                asymmetry_ratio = float("inf")
            elif b_val == 0:
                asymmetry_ratio = float("inf") if uncapped.get(parties[0]) else (a_val and float("inf"))
            else:
                asymmetry_ratio = (a_val or 0.0) / (b_val or 1.0)

            if asymmetry_ratio and asymmetry_ratio > 5:
                asymmetry_flag = "Critical"
            elif asymmetry_ratio and asymmetry_ratio > 3:
                asymmetry_flag = "High"
    except Exception:
        asymmetry_ratio = None
    return asymmetry_ratio, asymmetry_flag


def _detect_lease_specific_flags(obligation_graph: List[Dict[str, Any]], red_flags: List[Dict[str, Any]]) -> None:
    seen: set[tuple[str, str]] = set()
    for obligation in obligation_graph:
        clause_text = obligation.get("clause_text", "")
        text_lower = clause_text.lower()
        percent_match = PERCENT_PATTERN.search(text_lower)
        percent = int(percent_match.group(1)) if percent_match else 0
        day_match = DAY_PATTERN.search(text_lower)
        days = int(day_match.group(1)) if day_match else 0

        def add_once(category: str, why: str, fix: str, severity: str) -> None:
            key = (category, clause_text[:120])
            if key in seen:
                return
            seen.add(key)
            _add_flag(
                red_flags,
                category=category,
                description=clause_text,
                why=why,
                fix=fix,
                severity=severity,
            )

        if "rent" in text_lower and ("escalat" in text_lower or "cpi" in text_lower or "increase" in text_lower):
            if "cap" not in text_lower:
                add_once(
                    "Rent Escalation",
                    "Rent can rise unpredictably over time, which makes budgeting difficult.",
                    "Add an annual increase cap (for example 3%-5%) and define an objective formula.",
                    "High",
                )

        if any(k in text_lower for k in ("cam", "common area maintenance", "operating expense", "triple net")):
            if any(k in text_lower for k in ("any and all", "sole discretion", "as determined by landlord", "all costs")):
                add_once(
                    "Pass-Through Costs",
                    "The tenant may absorb broad building costs beyond base rent.",
                    "Limit reimbursable costs, cap annual increases, and require audit rights.",
                    "High",
                )

        if any(k in text_lower for k in ("repair", "maintenance")) and any(
            k in text_lower for k in ("structural", "roof", "foundation", "hvac")
        ):
            add_once(
                "Major Repair Responsibility",
                "You may be paying for major building repairs that are typically the landlord's responsibility.",
                "Move structural and major system repairs to landlord responsibility or set a hard cap.",
                "High",
            )

        if any(k in text_lower for k in ("personal guarantee", "personally liable", "guarantor", "guarantee")):
            add_once(
                "Personal Guarantee",
                "Your personal assets may be at risk if lease payments are missed.",
                "Limit the guarantee by dollar amount and duration, with automatic release conditions.",
                "Critical",
            )

        if "holdover" in text_lower and percent >= 150:
            add_once(
                "Holdover Penalty",
                "Staying after lease end may trigger heavy penalty rent.",
                "Reduce holdover rate to 125%-150% and include a short grace period.",
                "High" if percent < 200 else "Critical",
            )

        if "default" in text_lower and "cure" in text_lower and days and days <= 5:
            add_once(
                "Short Cure Window",
                "You may have too little time to fix a default before stronger remedies apply.",
                "Set cure periods to at least 10-15 days for payment defaults and longer for non-payment defaults.",
                "Critical",
            )

        if any(k in text_lower for k in ("accelerat", "all remaining rent", "entire balance due")):
            add_once(
                "Accelerated Rent",
                "After default, you could owe most or all future rent immediately.",
                "Remove acceleration language or require landlord to mitigate and credit replacement rent.",
                "Critical",
            )

        if any(k in text_lower for k in ("enter", "entry", "access")) and any(
            k in text_lower for k in ("without notice", "at any time", "any time")
        ):
            add_once(
                "Landlord Entry Rights",
                "Unrestricted access can disrupt operations and reduce privacy.",
                "Require prior written notice except genuine emergencies and limit entry to business hours.",
                "Moderate",
            )

        if any(k in text_lower for k in ("sublease", "sublet", "assign")) and any(
            k in text_lower for k in ("sole discretion", "absolute discretion", "may withhold consent")
        ):
            add_once(
                "Transfer Restrictions",
                "You may be blocked from assigning or subleasing even when reasonable.",
                "Require landlord consent not to be unreasonably withheld, delayed, or conditioned.",
                "High",
            )

        if "security deposit" in text_lower and any(k in text_lower for k in ("non-refundable", "forfeit", "waive")):
            add_once(
                "Deposit Forfeiture",
                "You may lose your security deposit more easily than expected.",
                "Make the deposit refundable, require itemized deductions, and set a clear return deadline.",
                "High",
            )

        if "relocat" in text_lower and "landlord" in text_lower:
            add_once(
                "Relocation Right",
                "The landlord may force relocation, which can hurt business continuity.",
                "Limit relocation to equivalent space, landlord-paid costs, and tenant approval rights.",
                "High",
            )

        if any(k in text_lower for k in ("late fee", "interest")) and percent >= 18:
            add_once(
                "Late Charges",
                "High interest or late fees can quickly increase total debt.",
                "Cap late fees, reduce interest, and add a short grace period.",
                "High",
            )


def detect_red_flags(
    liabilities: List[Dict[str, Any]], obligation_graph: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Return lease-focused red flags and supporting metrics."""
    red_flags: List[Dict[str, Any]] = []

    highest_indemnity_tier = _append_indemnity_flags(liabilities, red_flags)
    illusory, reasons = detect_illusory_cap(liabilities)
    if illusory:
        _add_flag(
            red_flags,
            category="Liability Cap",
            description="Liability cap may be weakened by carve-outs.",
            why="Some exceptions appear broad enough to bypass the cap for major claims.",
            fix="Narrow carve-outs and keep a clear overall cap for predictable downside.",
            severity="Critical",
        )

    _detect_lease_specific_flags(obligation_graph, red_flags)

    exp = compute_exposure_estimate(liabilities)
    totals = exp.get("totals", {})
    uncapped = exp.get("uncapped", {})
    asym_ratio, asym_flag = _compute_asymmetry(liabilities, totals, uncapped)

    survival_multiplier = 1.0
    for obligation in obligation_graph:
        text_lower = obligation.get("clause_text", "").lower()
        if (
            ("survive" in text_lower or "survival" in text_lower or "indefinite" in text_lower)
            and ("indemn" in text_lower or "liabil" in text_lower or "default" in text_lower)
        ):
            survival_multiplier = max(survival_multiplier, 1.3)

    control_imbalance = any(
        "sole discretion" in (obligation.get("clause_text", "").lower())
        or "exclusive right" in (obligation.get("clause_text", "").lower())
        for obligation in obligation_graph
    )

    return {
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
