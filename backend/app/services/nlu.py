"""
NLU pipeline: normalize text, spaCy tokenization, regex for dosage/qty,
fuzzy match against medicine_master (name + brand). Optional LLM disambiguation.
"""
import os
import re
from typing import Any, Optional

from app.utils import load_medicine_master, get_data_dir
from app.services.llm_client import disambiguate, DISAMBIGUATION_THRESHOLD

# Fuzzy matching
try:
    from rapidfuzz import process as rf_process
except ImportError:
    rf_process = None

# SpaCy optional
try:
    import spacy
    _nlp = None

    def _get_nlp():
        global _nlp
        if _nlp is None:
            try:
                _nlp = spacy.load("en_core_web_sm")
            except OSError:
                _nlp = spacy.blank("en")
        return _nlp
except Exception:
    spacy = None
    _get_nlp = None

# Thresholds
FUZZY_MATCH_THRESHOLD = 70
DISAMBIGUATE_BELOW = 60


def _normalize(text: str) -> str:
    """Lowercase and normalize whitespace."""
    return " ".join((text or "").lower().split())


def _extract_quantity(text: str) -> int:
    """Extract quantity from phrases like 'two', '2', 'a couple of', 'one box'."""
    text = _normalize(text)
    # Numbers
    m = re.search(r"\b(\d+)\s*(tablets?|pills?|capsules?|boxes?|strips?)?\b", text)
    if m:
        return int(m.group(1))
    # Words
    word_to_num = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "a couple": 2, "couple": 2, "few": 3, "several": 5,
    }
    for w, n in word_to_num.items():
        if re.search(rf"\b{w}\b", text):
            return n
    return 1


def _extract_dosage(text: str) -> Optional[str]:
    """Extract dosage like 50mg, 250 mg, 75mg."""
    m = re.search(r"\b(\d+)\s*mg\b", text, re.I)
    if m:
        return f"{m.group(1)}mg"
    return None


def _tokenize_for_match(text: str) -> str:
    """Return string used for fuzzy matching (normalized, maybe noun chunks)."""
    normalized = _normalize(text)
    if _get_nlp:
        try:
            doc = _get_nlp()(normalized)
            # Use noun chunks if available to focus on medicine-like phrases
            chunks = list(doc.noun_chunks)
            if chunks:
                return " ".join(c.text.lower() for c in chunks)
        except Exception:
            pass
    return normalized


def _build_choices(medicines: list[dict]) -> list[tuple[str, dict]]:
    """Build list of (search_string, medicine_dict) for fuzzy matching."""
    choices = []
    for m in medicines:
        name = (m.get("name") or "").strip()
        brand = (m.get("brand") or "").strip()
        choices.append((name, m))
        if brand and brand != name:
            choices.append((brand, m))
        if name and " " in name:
            choices.append((name.split()[0], m))  # first word
    return choices


def run_nlu(user_text: str, medicine_master: Optional[list[dict]] = None) -> dict[str, Any]:
    """
    Run full NLU pipeline. Returns:
    {
      "medicine_candidate": {"id", "name", "score", "brand"} or None,
      "quantity": int,
      "dosage": str or None,
      "raw_slots": {...}
    }
    """
    if medicine_master is None:
        medicine_master = load_medicine_master()
    raw_slots = {"raw_text": user_text, "quantity": None, "dosage": None, "medicine_phrase": None}
    quantity = _extract_quantity(user_text)
    dosage = _extract_dosage(user_text)
    raw_slots["quantity"] = quantity
    raw_slots["dosage"] = dosage

    search_str = _tokenize_for_match(user_text)
    raw_slots["medicine_phrase"] = search_str

    if not rf_process or not medicine_master:
        return {
            "medicine_candidate": None,
            "quantity": quantity,
            "dosage": dosage,
            "raw_slots": raw_slots,
        }

    choices = _build_choices(medicine_master)
    if not choices:
        return {
            "medicine_candidate": None,
            "quantity": quantity,
            "dosage": dosage,
            "raw_slots": raw_slots,
        }

    # Single best match by string
    strings_only = [c[0] for c in choices]
    result = rf_process.extractOne(search_str, strings_only, score_cutoff=FUZZY_MATCH_THRESHOLD)
    if result:
        matched_str, score, _ = result
        med = next(c[1] for c in choices if c[0] == matched_str)
        candidate = {
            "id": med.get("id"),
            "name": med.get("name"),
            "brand": med.get("brand"),
            "score": score,
        }
        if score < DISAMBIGUATE_BELOW and os.environ.get("OPENAI_API_KEY"):
            # Get top-5 by score for disambiguation
            all_matches = rf_process.extract(search_str, strings_only, limit=5)
            candidates_for_llm = []
            seen_ids = set()
            for s, sc, _ in all_matches:
                m = next(c[1] for c in choices if c[0] == s)
                if m.get("id") not in seen_ids:
                    seen_ids.add(m.get("id"))
                    candidates_for_llm.append({"id": m.get("id"), "name": m.get("name"), "brand": m.get("brand"), "score": sc})
            dis = disambiguate(user_text, candidates_for_llm)
            if dis.get("selected_id"):
                med = next((x for x in medicine_master if x.get("id") == dis["selected_id"]), med)
                candidate = {"id": med.get("id"), "name": med.get("name"), "brand": med.get("brand"), "score": score}
            raw_slots["disambiguation"] = dis
        return {
            "medicine_candidate": candidate,
            "quantity": quantity,
            "dosage": dosage,
            "raw_slots": raw_slots,
        }

    # No match above threshold: try LLM with top-5
    all_matches = rf_process.extract(search_str, strings_only, limit=5) if search_str else []
    candidates_for_llm = []
    seen_ids = set()
    for s, sc, _ in all_matches:
        m = next(c[1] for c in choices if c[0] == s)
        if m.get("id") not in seen_ids:
            seen_ids.add(m.get("id"))
            candidates_for_llm.append({"id": m.get("id"), "name": m.get("name"), "brand": m.get("brand"), "score": sc})
    if candidates_for_llm and os.environ.get("OPENAI_API_KEY"):
        dis = disambiguate(user_text, candidates_for_llm)
        if dis.get("selected_id"):
            med = next((x for x in medicine_master if x.get("id") == dis["selected_id"]), None)
            if med:
                return {
                    "medicine_candidate": {"id": med.get("id"), "name": med.get("name"), "brand": med.get("brand"), "score": 0},
                    "quantity": quantity,
                    "dosage": dosage,
                    "raw_slots": raw_slots,
                }
    return {
        "medicine_candidate": None,
        "quantity": quantity,
        "dosage": dosage,
        "raw_slots": raw_slots,
    }
