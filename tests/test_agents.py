import pytest

from src.contract_agent import (
    structuring,
    liability_extraction,
    red_flag_detection,
    risk_scoring,
    output,
)


def test_placeholder():
    text = "This Agreement is between Alpha Co and Beta LLC. Alpha Co shall indemnify Beta LLC for any third-party claims. Liability cap of $10000 except for data breach."
    sections = structuring.extract_sections(text)
    parties = structuring.extract_parties(text)
    graph = structuring.build_obligation_graph(sections, parties)
    liabilities = liability_extraction.extract_liabilities(graph)
    metrics = red_flag_detection.detect_red_flags(liabilities, graph)
    scoring = risk_scoring.score_contract(metrics)
    assert isinstance(metrics, dict)
    assert 'red_flags' in metrics
    assert 'final_score' in scoring or 'final_score' in scoring
