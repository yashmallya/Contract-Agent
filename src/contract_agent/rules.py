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
    # More rules would go here.
}
