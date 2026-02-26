"""Document Structuring Agent

Performs structural parsing (layer 1) including party extraction and
building a machine-readable obligation graph.
"""

from typing import List, Dict, Tuple, Optional
import re


def extract_sections(text: str) -> List[Dict[str, str]]:
    """Naive section splitter based on common headings and keywords.

    Returns a list of {type, text}. This is intentionally lightweight; the
    downstream agents expect a list of segments to analyze.
    """
    headings = [
        'definitions', 'indemnity', 'limitation', 'limitation of liability',
        'termination', 'payment', 'governing law', 'intellectual property',
        'confidentiality', 'warranties', 'dispute', 'force majeure',
        'assignment', 'change of control'
    ]

    segments: List[Dict[str, str]] = []
    # Try splitting by common heading lines
    pattern = re.compile(r"(^|\n)([A-Z][A-Za-z0-9 \-]{1,80})\n[-=]{2,}|(^|\n)(\b(?:" + '|'.join(headings) + r")\b)[:\n]", re.IGNORECASE)
    last = 0
    matches = list(pattern.finditer(text))
    if not matches:
        return [{'type': 'full_text', 'text': text}]

    for i, m in enumerate(matches):
        start = m.start()
        heading = (m.group(2) or m.group(4) or '').strip()
        # previous content
        if i == 0 and start > 0:
            segments.append({'type': 'prelude', 'text': text[0:start].strip()})
        # find end = next match start or end of text
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        content = text[start:end].strip()
        segments.append({'type': heading.lower() or 'section', 'text': content})
    return segments


def extract_parties(text: str) -> Dict[str, Optional[str]]:
    """Try to extract Party A and Party B names and drafting party.

    Uses heuristics: look for "This Agreement is between X and Y" or
    "between X (\"Party A\") and Y (\"Party B\")" patterns.
    """
    parties = {'party_a': None, 'party_b': None, 'drafting_party': None}
    # common pattern
    m = re.search(r"this (agreement|contract)[\s\S]{0,80}?between\s+([^,\n]+?)\s+(?:\(.*?\))?\s+and\s+([^,\n]+)", text, re.IGNORECASE)
    if m:
        parties['party_a'] = m.group(2).strip()
        parties['party_b'] = m.group(3).strip()
        return parties

    # alternative: look for "Party A" labelled
    m2 = re.findall(r"([A-Z][A-Za-z0-9 &.,\-]{2,80})\s*\((?:Party )?A\)", text)
    if m2:
        parties['party_a'] = m2[0].strip()
    m3 = re.findall(r"([A-Z][A-Za-z0-9 &.,\-]{2,80})\s*\((?:Party )?B\)", text)
    if m3:
        parties['party_b'] = m3[0].strip()

    # Infer drafting party by searching for addresses like "drafted by" or "prepared by"
    m4 = re.search(r"drafted by\s+([A-Z][A-Za-z0-9 &.,\-]{2,80})", text, re.IGNORECASE)
    if m4:
        parties['drafting_party'] = m4.group(1).strip()

    return parties


def build_obligation_graph(segments: List[Dict[str, str]], parties: Dict[str, Optional[str]]) -> List[Dict[str, object]]:
    """Build a lightweight obligation graph from segments.

    For each sentence, detect obligated party, benefiting party, obligation type,
    financial exposure (if mentioned), duration and cap.
    This returns a list of obligation objects as described in the spec.
    """
    graph: List[Dict[str, object]] = []
    party_names = [p for p in (parties.get('party_a'), parties.get('party_b')) if p]

    # tokenize sentences simply
    text = '\n'.join(s.get('text', '') for s in segments)
    import re as _re
    sentences = [s.strip() for s in _re.split(r'(?<=[\.!?])\s+', text) if s.strip()]

    for s in sentences:
        obj = {
            'clause_text': s,
            'obligated_party': None,
            'benefiting_party': None,
            'obligation_type': None,
            'financial_exposure': None,
            'duration': None,
            'cap': None,
            'exceptions': []
        }

        # obligated party heuristics
        for pname in party_names:
            if pname and pname.lower() in s.lower():
                # naive: if name precedes 'shall' assume obligated
                if 'shall' in s.lower() or 'must' in s.lower() or 'will' in s.lower() or 'agrees to' in s.lower():
                    obj['obligated_party'] = pname
                    # other party benefits
                    other = [x for x in party_names if x != pname]
                    obj['benefiting_party'] = other[0] if other else None
                    break

        # fallback: presence of 'shall' assign to drafter if known
        if not obj['obligated_party'] and ('shall' in s.lower() or 'must' in s.lower()):
            obj['obligated_party'] = parties.get('drafting_party')

        # obligation type detection
        if 'indemnif' in s.lower():
            obj['obligation_type'] = 'indemnity'
        elif 'liable' in s.lower() or 'liability' in s.lower():
            obj['obligation_type'] = 'liability'
        elif 'terminate' in s.lower() or 'termination' in s.lower():
            obj['obligation_type'] = 'termination'
        elif 'payment' in s.lower() or 'fee' in s.lower() or 'invoice' in s.lower():
            obj['obligation_type'] = 'payment'

        # cap detection
        cap_match = _re.search(r'cap(?:s)?\s*(?:of)?\s*(?:liability)?\s*(?:at|to|=)?\s*\$?([0-9,]+)', s, _re.IGNORECASE)
        if cap_match:
            obj['cap'] = cap_match.group(1).replace(',', '')

        # exceptions: look for 'except' or 'notwithstanding' clauses
        if 'except' in s.lower() or 'notwithstanding' in s.lower():
            obj['exceptions'].append(s)

        # financial exposure detection (very coarse)
        money = _re.search(r'\$([0-9,]+)', s)
        if money:
            obj['financial_exposure'] = money.group(1).replace(',', '')

        graph.append(obj)

    return graph

