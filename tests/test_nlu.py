"""
Tests for NLU: fuzzy matching and slot extraction with sample sentences.
"""
import os
import pytest
from app.services.nlu import run_nlu, _extract_quantity, _extract_dosage, _normalize
from app.utils import load_medicine_master

# Ensure we use test data
DATA_DIR = os.environ.get("DATA_DIR")
assert DATA_DIR, "DATA_DIR must be set (conftest)"


def test_normalize():
    assert _normalize("  Two   Aspirin  ") == "two aspirin"


def test_extract_quantity():
    assert _extract_quantity("I need two tablets") == 2
    assert _extract_quantity("give me 5 pills") == 5
    assert _extract_quantity("one box") == 1
    assert _extract_quantity("aspirin") == 1


def test_extract_dosage():
    assert _extract_dosage("Aspirin 75mg") == "75mg"
    assert _extract_dosage("Losartan 50 mg") == "50mg"
    assert _extract_dosage("no dosage here") is None


def test_nlu_aspirin():
    """User asks for Aspirin - should match med_aspirin_75."""
    master = load_medicine_master()
    result = run_nlu("I need two Aspirin 75 mg tablets", medicine_master=master)
    assert result["quantity"] == 2
    assert result["dosage"] == "75mg"
    cand = result.get("medicine_candidate")
    assert cand is not None
    assert cand.get("id") == "med_aspirin_75"
    assert cand.get("name") and "Aspirin" in cand["name"]


def test_nlu_losartan():
    """User says Losartan - fuzzy match to med_losartan_50."""
    master = load_medicine_master()
    result = run_nlu("I want 30 Losartan 50mg", medicine_master=master)
    assert result["quantity"] == 30
    cand = result.get("medicine_candidate")
    assert cand is not None
    assert cand.get("id") == "med_losartan_50"


def test_nlu_metformin():
    """User says Metformin - match to med_metformin_500."""
    master = load_medicine_master()
    result = run_nlu("Need 60 metformin 500mg tablets", medicine_master=master)
    assert result["quantity"] == 60
    cand = result.get("medicine_candidate")
    assert cand is not None
    assert cand.get("id") == "med_metformin_500"


def test_nlu_gibberish_low_match():
    """Gibberish medicine name may not match above threshold."""
    master = load_medicine_master()
    result = run_nlu("I need 10 xyzzy pills", medicine_master=master)
    assert result["quantity"] == 10
    # May or may not have candidate depending on threshold
    assert "raw_slots" in result
