"""Entry point for the Contract Agent system."""

from src.contract_agent import (
    structuring,
    liability_extraction,
    red_flag_detection,
    risk_scoring,
    output,
)


def analyze_contract(text: str) -> str:
    # Layer 1: structural parsing
    sections = structuring.extract_sections(text)
    parties = structuring.extract_parties(text)
    obligation_graph = structuring.build_obligation_graph(sections, parties)

    # Layer 2: liability extraction
    liabilities = liability_extraction.extract_liabilities(obligation_graph)

    # Layer 3-4: red flags (includes illusory cap detection, asymmetry, etc.)
    metrics = red_flag_detection.detect_red_flags(liabilities, obligation_graph)

    # Layer 5: scoring
    scoring = risk_scoring.score_contract(metrics)

    # Build a short summary
    summary = f"Parties: {parties.get('party_a') or 'Unknown'} vs {parties.get('party_b') or 'Unknown'}; Detected {len(liabilities)} liability clauses."

    return output.format_output(summary, liabilities, metrics, scoring.get('final_score', 0), scoring.get('risk_level', 'Low'))


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python run_agent.py <contract_text_file>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, 'r') as f:
        text = f.read()

    print(analyze_contract(text))
