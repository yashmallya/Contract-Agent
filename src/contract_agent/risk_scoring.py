"""Risk Scoring Agent (v2)

Implements the cluster-based scoring and dynamic multipliers described in the
new rulebook. Supports scores >100 for structural risk.
"""

from typing import Any, Dict


# Cluster maximums
CLUSTERS = {
    "financial_exposure": 30,
    "indemnity": 25,
    "liability_structure": 20,
    "termination_lockin": 15,
    "regulatory_ip": 20,
}


def asymmetry_modifier(asymmetry_ratio: Any) -> float:
    try:
        if asymmetry_ratio is None:
            return 1.0
        if asymmetry_ratio == float("inf"):
            return 1.5
        ratio = float(asymmetry_ratio)
        if ratio > 5:
            return 1.5
        if ratio > 3:
            return 1.3
        if ratio > 2:
            return 1.15
        return 1.0
    except Exception:
        return 1.0


def compute_cluster_scores(metrics: Dict[str, Any]) -> Dict[str, float]:
    # Basic mapping from detected flags / metrics to cluster scores.
    clusters = {k: 0.0 for k in CLUSTERS.keys()}

    # Financial: compounded interest, acceleration, unbounded exposure
    if metrics.get("exposure_totals"):
        clusters["financial_exposure"] += min(
            CLUSTERS["financial_exposure"], sum(metrics["exposure_totals"].values()) / 1000.0
        )
    if metrics.get("survival_multiplier", 1.0) > 1.0:
        clusters["financial_exposure"] += 5
    if metrics.get("control_imbalance"):
        clusters["financial_exposure"] += 3

    # Indemnity: tier mapping
    tier = metrics.get("highest_indemnity_tier", 1)
    if tier <= 1:
        clusters["indemnity"] = 2
    elif tier == 2:
        clusters["indemnity"] = 8
    elif tier == 3:
        clusters["indemnity"] = 15
    elif tier == 4:
        clusters["indemnity"] = 20
    else:
        clusters["indemnity"] = CLUSTERS["indemnity"]

    # Liability structure: illusory cap and uncapped parties
    if metrics.get("illusory_cap"):
        clusters["liability_structure"] += 18
    if metrics.get("uncapped_parties"):
        clusters["liability_structure"] += 15

    # Termination and lock-in
    if any(flag["category"] == "Termination" for flag in metrics.get("red_flags", [])):
        clusters["termination_lockin"] += 12
    if metrics.get("asymmetry_severity") == "Critical":
        clusters["termination_lockin"] += 5

    # Regulatory & IP
    for red_flag in metrics.get("red_flags", []):
        if red_flag["category"] in ("Regulatory", "IP", "Data"):
            clusters["regulatory_ip"] += 10

    # Cap cluster values at defined maxima
    for cluster_name in clusters:
        clusters[cluster_name] = min(CLUSTERS[cluster_name], clusters[cluster_name])

    return clusters


SEVERITY_MULTIPLIERS = {
    "uncapped+indemnity": 2.5,
    "indemnity_negligence": 3.0,
    "survival_indefinite": 1.5,
    "asymmetric_termination": 1.7,
    "regulatory_pass_through": 2.0,
    "foreign_arbitration": 1.4,
}


def score_contract(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Compute final structural risk score based on cluster scores and modifiers.

    metrics: result from `detect_red_flags` that contains cluster signals.
    """
    clusters = compute_cluster_scores(metrics)
    base_score = sum(clusters.values())

    # Apply severity multipliers based on flags
    multiplier = 1.0
    # uncapped + indemnity
    if metrics.get("uncapped_parties") and metrics.get("highest_indemnity_tier", 1) >= 4:
        multiplier *= SEVERITY_MULTIPLIERS["uncapped+indemnity"]
    # indemnity for other party negligence
    if metrics.get("highest_indemnity_tier", 1) >= 3:
        multiplier *= 1.2
    # survival
    multiplier *= metrics.get("survival_multiplier", 1.0)

    # asymmetry modifier
    asym_mod = asymmetry_modifier(metrics.get("asymmetry_ratio"))
    multiplier *= asym_mod

    final_score = base_score * multiplier

    # map to level
    level = "Low"
    if final_score <= 40:
        level = "Low"
    elif final_score <= 70:
        level = "Moderate"
    elif final_score <= 100:
        level = "High"
    else:
        level = "Critical Structural Risk"

    return {
        "cluster_scores": clusters,
        "base_score": base_score,
        "multiplier": multiplier,
        "final_score": final_score,
        "risk_level": level,
    }
