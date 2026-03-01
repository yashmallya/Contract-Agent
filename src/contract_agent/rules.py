"""Rule definitions and patterns for red flag detection."""

# Example patterns, to be expanded with full rule set from design
RULES = {
    "Unlimited or Asymmetric Liability": {
        "patterns": [
            "Unlimited liability",
            "without limitation",
            "In no event shall",
        ],
        "severity": "Critical",
    },
    # More rules would go here.{
  "lease_vetting_rules": [
    {
      "category": "Financial",
      "rule_id": "FIN-001",
      "title": "Rent Escalation Cap",
      "risk_level": "High",
      "trigger_keywords": ["escalation", "increase", "adjustment", "index"],
      "logic": "Flag if annual rent increase exceeds 5% or is not tied to a specific index (CPI).",
      "ideal_clause": "Annual rent shall increase by no more than 3% or the CPI, whichever is lower."
    },
    {
      "category": "Operations",
      "rule_id": "OPS-001",
      "title": "Holdover Rent",
      "risk_level": "Medium",
      "trigger_keywords": ["holdover", "expiration", "staying over"],
      "logic": "Flag if holdover rent exceeds 150% of the last monthly rent.",
      "mitigation": "Negotiate 125% for the first 30 days of holdover."
    },
    {
      "category": "Exit & Termination",
      "rule_id": "EXIT-001",
      "title": "Mutual Termination",
      "risk_level": "Critical",
      "trigger_keywords": ["termination", "break clause", "cancellation"],
      "logic": "Flag if only the Landlord has the right to terminate for convenience (without cause).",
      "ideal_clause": "Either party may terminate this lease with 90 days written notice."
    },
    {
      "category": "Liability",
      "rule_id": "LIAB-001",
      "title": "Indemnification Reciprocity",
      "risk_level": "High",
      "trigger_keywords": ["indemnify", "hold harmless", "liability"],
      "logic": "Flag if the Tenant indemnifies the Landlord, but there is no reciprocal clause for Landlord negligence.",
      "mitigation": "Ensure mutual indemnification for third-party claims."
    }
  ]
}

