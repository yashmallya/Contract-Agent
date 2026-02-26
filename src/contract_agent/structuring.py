"""Document Structuring Agent.

Performs structural parsing (layer 1) including party extraction and
building a machine-readable obligation graph.
"""

from typing import Dict, List, Optional
import re

SECTION_HEADINGS = [
    "definitions",
    "indemnity",
    "limitation",
    "limitation of liability",
    "termination",
    "payment",
    "governing law",
    "intellectual property",
    "confidentiality",
    "warranties",
    "dispute",
    "force majeure",
    "assignment",
    "change of control",
]

SECTION_PATTERN = re.compile(
    r"(^|\n)([A-Z][A-Za-z0-9 \-]{1,80})\n[-=]{2,}|(^|\n)(\b(?:"
    + "|".join(SECTION_HEADINGS)
    + r")\b)[:\n]",
    re.IGNORECASE,
)
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[\.!?])\s+")
CAP_PATTERN = re.compile(
    r"cap(?:s)?\s*(?:of)?\s*(?:liability)?\s*(?:at|to|=)?\s*\$?([0-9,]+)",
    re.IGNORECASE,
)
MONEY_PATTERN = re.compile(r"\$([0-9,]+)")


def extract_sections(text: str) -> List[Dict[str, str]]:
    """Naive section splitter based on common headings and keywords."""
    matches = list(SECTION_PATTERN.finditer(text))
    if not matches:
        return [{"type": "full_text", "text": text}]

    segments: List[Dict[str, str]] = []
    for i, match in enumerate(matches):
        start = match.start()
        heading = (match.group(2) or match.group(4) or "").strip()
        if i == 0 and start > 0:
            segments.append({"type": "prelude", "text": text[0:start].strip()})

        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        segments.append({"type": heading.lower() or "section", "text": content})

    return segments


def extract_parties(text: str) -> Dict[str, Optional[str]]:
    """Try to extract Party A and Party B names and drafting party."""
    parties = {"party_a": None, "party_b": None, "drafting_party": None}

    match = re.search(
        r"this (agreement|contract)[\s\S]{0,80}?between\s+([^,\n]+?)\s+(?:\(.*?\))?\s+and\s+([^,\n]+)",
        text,
        re.IGNORECASE,
    )
    if match:
        parties["party_a"] = match.group(2).strip()
        parties["party_b"] = match.group(3).strip()
        return parties

    party_a_matches = re.findall(r"([A-Z][A-Za-z0-9 &.,\-]{2,80})\s*\((?:Party )?A\)", text)
    if party_a_matches:
        parties["party_a"] = party_a_matches[0].strip()

    party_b_matches = re.findall(r"([A-Z][A-Za-z0-9 &.,\-]{2,80})\s*\((?:Party )?B\)", text)
    if party_b_matches:
        parties["party_b"] = party_b_matches[0].strip()

    drafted_by = re.search(r"drafted by\s+([A-Z][A-Za-z0-9 &.,\-]{2,80})", text, re.IGNORECASE)
    if drafted_by:
        parties["drafting_party"] = drafted_by.group(1).strip()

    return parties


def _detect_obligation_type(sentence: str) -> Optional[str]:
    sentence_lower = sentence.lower()
    if "indemnif" in sentence_lower:
        return "indemnity"
    if "liable" in sentence_lower or "liability" in sentence_lower:
        return "liability"
    if "terminate" in sentence_lower or "termination" in sentence_lower:
        return "termination"
    if "payment" in sentence_lower or "fee" in sentence_lower or "invoice" in sentence_lower:
        return "payment"
    return None


def build_obligation_graph(
    segments: List[Dict[str, str]], parties: Dict[str, Optional[str]]
) -> List[Dict[str, object]]:
    """Build a lightweight obligation graph from segmented contract text."""
    party_names = [name for name in (parties.get("party_a"), parties.get("party_b")) if name]
    text = "\n".join(segment.get("text", "") for segment in segments)
    sentences = [sentence.strip() for sentence in SENTENCE_SPLIT_PATTERN.split(text) if sentence.strip()]

    graph: List[Dict[str, object]] = []
    for sentence in sentences:
        sentence_lower = sentence.lower()
        obligation = {
            "clause_text": sentence,
            "obligated_party": None,
            "benefiting_party": None,
            "obligation_type": None,
            "financial_exposure": None,
            "duration": None,
            "cap": None,
            "exceptions": [],
        }

        for party_name in party_names:
            if party_name and party_name.lower() in sentence_lower:
                if (
                    "shall" in sentence_lower
                    or "must" in sentence_lower
                    or "will" in sentence_lower
                    or "agrees to" in sentence_lower
                ):
                    obligation["obligated_party"] = party_name
                    other_parties = [name for name in party_names if name != party_name]
                    obligation["benefiting_party"] = other_parties[0] if other_parties else None
                    break

        if not obligation["obligated_party"] and ("shall" in sentence_lower or "must" in sentence_lower):
            obligation["obligated_party"] = parties.get("drafting_party")

        obligation["obligation_type"] = _detect_obligation_type(sentence)

        cap_match = CAP_PATTERN.search(sentence)
        if cap_match:
            obligation["cap"] = cap_match.group(1).replace(",", "")

        if "except" in sentence_lower or "notwithstanding" in sentence_lower:
            obligation["exceptions"].append(sentence)

        money_match = MONEY_PATTERN.search(sentence)
        if money_match:
            obligation["financial_exposure"] = money_match.group(1).replace(",", "")

        graph.append(obligation)

    return graph
