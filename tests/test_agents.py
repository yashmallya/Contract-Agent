import json

from src.contract_agent import (
    structuring,
    liability_extraction,
    red_flag_detection,
    risk_scoring,
    output,
)
from run_agent import analyze_contract


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


def test_lease_specific_flags_and_resolution_text():
    lease_text = """
    This Lease Agreement is between Downtown Landlord LLC and Green Cafe Inc as Tenant.
    Base rent shall increase annually by CPI with no cap.
    Tenant shall pay all CAM charges, operating expenses, taxes, insurance, and management fees as additional rent.
    Tenant is responsible for structural repairs including roof, foundation, and HVAC replacement.
    The guarantor shall be personally liable for all obligations under this lease.
    Upon default, Tenant has 3 days to cure and Landlord may accelerate all remaining rent.
    Holdover rent shall be 200% of base rent.
    """
    result = json.loads(analyze_contract(lease_text))
    assert result["contract_summary"].lower().startswith("lease vetting summary")
    assert len(result["red_flags"]) > 0
    assert any(flag.get("category") == "Personal Guarantee" for flag in result["red_flags"])
    assert all(flag.get("resolution") for flag in result["red_flags"])
    assert all(clause.get("resolution") for clause in result["liability_clauses"])


def test_plain_language_liability_fields_present():
    text = """
    Lease between Landlord A and Tenant B.
    Tenant shall pay late interest at 24% and late fee of 10%.
    Security deposit is non-refundable.
    """
    sections = structuring.extract_sections(text)
    parties = structuring.extract_parties(text)
    graph = structuring.build_obligation_graph(sections, parties)
    liabilities = liability_extraction.extract_liabilities(graph)
    assert len(liabilities) > 0
    assert any(item.get("reason") for item in liabilities)
    assert any(item.get("recommendation") for item in liabilities)
    assert any(item.get("resolution") for item in liabilities)
