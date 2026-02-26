import pytest

from src.contract_agent import (
    structuring,
    liability_extraction,
    red_flag_detection,
    risk_scoring,
    output,
)


def test_placeholder():
    assert structuring.extract_sections("") == []
    assert liability_extraction.extract_liabilities([]) == []
    assert red_flag_detection.detect_red_flags([], []) == []
    assert risk_scoring.score_contract([])["overall_risk_score"] == 0
