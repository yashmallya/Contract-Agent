"""Entry point for the Contract Agent system."""

from src.contract_agent import (
    structuring,
    liability_extraction,
    red_flag_detection,
    risk_scoring,
    output,
)


def analyze_contract(text: str) -> str:
    sections = structuring.extract_sections(text)
    liabilities = liability_extraction.extract_liabilities(sections)
    red_flags = red_flag_detection.detect_red_flags(liabilities, sections)
    scoring = risk_scoring.score_contract(red_flags)
    summary = ""  # could be built from sections
    return output.format_output(summary, liabilities, red_flags, scoring.get('overall_risk_score', 0), scoring.get('risk_level', 'Low'))


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python run_agent.py <contract_text_file>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, 'r') as f:
        text = f.read()

    print(analyze_contract(text))
