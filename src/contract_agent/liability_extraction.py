"""Liability Extraction Agent.

Lease-focused extraction and normalization for downstream risk analysis.
"""

from typing import Dict, List, Tuple
import re

LEASE_LIABILITY_KEYWORDS = (
    "lease",
    "tenant",
    "landlord",
    "rent",
    "additional rent",
    "cam",
    "common area maintenance",
    "operating expense",
    "triple net",
    "security deposit",
    "holdover",
    "repair",
    "maintenance",
    "sublease",
    "sublet",
    "assignment",
    "default",
    "cure",
    "indemn",
    "guarant",
    "evict",
    "attorney",
    "late fee",
)
DAY_PATTERN = re.compile(r"(\d{1,3})\s*day")
PERCENT_PATTERN = re.compile(r"(\d{1,3})\s*%")


def _contains_any(text_lower: str, keywords: Tuple[str, ...]) -> bool:
    return any(keyword in text_lower for keyword in keywords)


def _extract_int(pattern: re.Pattern, text_lower: str) -> int:
    match = pattern.search(text_lower)
    if not match:
        return 0
    try:
        return int(match.group(1))
    except Exception:
        return 0


def _classify_lease_liability(clause_text: str, obligation_type: str) -> Dict[str, str]:
    text_lower = clause_text.lower()
    days = _extract_int(DAY_PATTERN, text_lower)
    percent = _extract_int(PERCENT_PATTERN, text_lower)

    if _contains_any(text_lower, ("personal guarantee", "personally liable", "guarantor", "guarantee")):
        return {
            "risk_type": "Personal Guarantee",
            "severity": "Critical",
            "reason": "This can make you personally responsible for lease debt, not just your business.",
            "recommendation": "Limit the guarantee by amount and time, and add automatic release after consistent on-time payments.",
        }

    if "holdover" in text_lower:
        severity = "Critical" if percent >= 175 else "High"
        return {
            "risk_type": "Holdover Penalty",
            "severity": severity,
            "reason": "Staying past lease end may trigger a steep rent penalty.",
            "recommendation": "Cap holdover rent at 125%-150% and add a short grace period for move-out delays.",
        }

    if _contains_any(text_lower, ("cam", "common area maintenance", "operating expense", "triple net")):
        return {
            "risk_type": "Extra Charges",
            "severity": "High",
            "reason": "Your total monthly cost can rise from pass-through charges beyond base rent.",
            "recommendation": "Set clear charge definitions, annual caps, and audit rights. Exclude capital improvements and landlord overhead.",
        }

    if _contains_any(text_lower, ("repair", "maintenance")) and _contains_any(
        text_lower, ("structural", "roof", "foundation", "hvac")
    ):
        return {
            "risk_type": "Repair Burden",
            "severity": "High",
            "reason": "You may pay for major building repairs that are usually a landlord responsibility.",
            "recommendation": "Shift structural, roof, and major system repairs to landlord or split costs with a clear cap.",
        }

    if "default" in text_lower and "cure" in text_lower and days and days <= 5:
        return {
            "risk_type": "Short Cure Period",
            "severity": "Critical",
            "reason": "You may have very little time to fix a problem before default remedies apply.",
            "recommendation": "Ask for at least 10-15 days to cure monetary defaults and 20-30 days for non-monetary defaults.",
        }

    if _contains_any(text_lower, ("accelerat", "all remaining rent", "entire balance")):
        return {
            "risk_type": "Accelerated Rent",
            "severity": "Critical",
            "reason": "If you default, you could owe most or all future rent immediately.",
            "recommendation": "Remove acceleration or require landlord to mitigate damages and credit replacement rent.",
        }

    if "security deposit" in text_lower and _contains_any(text_lower, ("non-refundable", "forfeit", "waive")):
        return {
            "risk_type": "Security Deposit Risk",
            "severity": "High",
            "reason": "You may lose your deposit even without major damage.",
            "recommendation": "Require a refundable deposit, itemized deductions, and a return deadline (for example 30 days).",
        }

    if "security deposit" in text_lower and days and days > 45:
        return {
            "risk_type": "Security Deposit Delay",
            "severity": "Moderate",
            "reason": "Deposit return timing is slow, which ties up your cash longer than usual.",
            "recommendation": "Reduce return timeline to 30 days and require itemized statements for any deductions.",
        }

    if _contains_any(text_lower, ("sublease", "sublet", "assign")) and _contains_any(
        text_lower, ("sole discretion", "absolute discretion", "may withhold consent")
    ):
        return {
            "risk_type": "Assignment/Sublease Restriction",
            "severity": "High",
            "reason": "You may be blocked from transferring the lease even for reasonable business changes.",
            "recommendation": "Add a standard that consent cannot be unreasonably withheld, delayed, or conditioned.",
        }

    if "rent" in text_lower and _contains_any(text_lower, ("escalat", "cpi", "increase")):
        return {
            "risk_type": "Rent Escalation",
            "severity": "High",
            "reason": "Rent can rise faster than expected and hurt long-term affordability.",
            "recommendation": "Set annual increase caps and define a clear formula with a maximum percentage.",
        }

    if _contains_any(text_lower, ("enter", "entry", "access")) and _contains_any(
        text_lower, ("without notice", "at any time", "any time")
    ):
        return {
            "risk_type": "Landlord Access",
            "severity": "Moderate",
            "reason": "You may have limited privacy and business disruption from frequent entry.",
            "recommendation": "Require advance notice except for emergencies and limit entry to business hours.",
        }

    if "indemn" in text_lower and _contains_any(text_lower, ("any and all", "regardless", "no cap", "uncap")):
        return {
            "risk_type": "Broad Indemnity",
            "severity": "Critical",
            "reason": "You could be responsible for very broad third-party costs with no financial cap.",
            "recommendation": "Narrow indemnity to your direct fault, exclude landlord negligence, and add a liability cap.",
        }

    if _contains_any(text_lower, ("late fee", "interest")):
        severity = "High" if percent >= 18 else "Moderate"
        return {
            "risk_type": "Late Fees & Interest",
            "severity": severity,
            "reason": "Late charges can stack quickly and increase total lease cost.",
            "recommendation": "Reduce late fees, cap interest, and add a short grace period before charges apply.",
        }

    if obligation_type in ("lease_payment", "payment"):
        return {
            "risk_type": "Payment Obligation",
            "severity": "Low",
            "reason": "This clause sets what and when you must pay under the lease.",
            "recommendation": "Confirm exact amounts, due dates, and any penalties are clearly defined.",
        }

    if obligation_type == "maintenance":
        return {
            "risk_type": "Maintenance Obligation",
            "severity": "Low",
            "reason": "This clause defines upkeep responsibilities for the property.",
            "recommendation": "Split minor vs major repairs clearly so there is no ambiguity later.",
        }

    return {
        "risk_type": "Lease Liability",
        "severity": "Low",
        "reason": "This clause creates a legal responsibility under the lease.",
        "recommendation": "Clarify responsibility, cost cap, and timelines in plain language.",
    }


def extract_liabilities(obligation_graph: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Extract lease liabilities and attach plain-language explanations."""
    liabilities: List[Dict[str, object]] = []
    for obligation in obligation_graph:
        obligation_type = obligation.get("obligation_type") or ""
        clause_text = obligation.get("clause_text") or ""
        text_lower = clause_text.lower()

        is_liability_related = (
            obligation_type
            in ("indemnity", "liability", "payment", "lease_payment", "maintenance", "security_deposit", "default")
            or "liab" in text_lower
            or "indemn" in text_lower
            or _contains_any(text_lower, LEASE_LIABILITY_KEYWORDS)
        )
        if not is_liability_related:
            continue

        explanation = _classify_lease_liability(clause_text, obligation_type)
        liabilities.append(
            {
                "clause_text": clause_text,
                "obligated_party": obligation.get("obligated_party"),
                "benefiting_party": obligation.get("benefiting_party"),
                "obligation_type": obligation_type or "unknown",
                "financial_exposure": obligation.get("financial_exposure"),
                "cap": obligation.get("cap"),
                "exceptions": obligation.get("exceptions") or [],
                "risk_type": explanation["risk_type"],
                "severity": explanation["severity"],
                "reason": explanation["reason"],
                "recommendation": explanation["recommendation"],
                "resolution": explanation["recommendation"],
            }
        )
    return liabilities
