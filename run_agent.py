"""Entry point for the Contract Agent system."""

from pathlib import Path

from src.contract_agent import (
    liability_extraction,
    output,
    red_flag_detection,
    risk_scoring,
    structuring,
)


def _build_summary(parties: dict, liabilities: list) -> str:
    return (
        f"Parties: {parties.get('party_a') or 'Unknown'} vs "
        f"{parties.get('party_b') or 'Unknown'}; "
        f"Detected {len(liabilities)} liability clauses."
    )


def analyze_contract(text: str) -> str:
    """Run the full contract-analysis pipeline and return JSON text."""
    sections = structuring.extract_sections(text)
    parties = structuring.extract_parties(text)
    obligation_graph = structuring.build_obligation_graph(sections, parties)

    liabilities = liability_extraction.extract_liabilities(obligation_graph)
    metrics = red_flag_detection.detect_red_flags(liabilities, obligation_graph)
    scoring = risk_scoring.score_contract(metrics)

    return output.format_output(
        _build_summary(parties, liabilities),
        liabilities,
        metrics,
        scoring.get("final_score", 0),
        scoring.get("risk_level", "Low"),
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python run_agent.py <contract_text_file>")
        sys.exit(1)

    path = Path(sys.argv[1])
    print(analyze_contract(path.read_text()))
