"""
Tests for Safety Engine: prescription required, low stock, full approval.
"""
import pytest
from app.services.safety_engine import evaluate, update_stock, reload_master


def _nlu_result(med_id: str, name: str, qty: int = 1):
    return {
        "medicine_candidate": {"id": med_id, "name": name, "score": 90},
        "quantity": qty,
        "dosage": None,
        "raw_slots": {},
    }


def test_prescription_required():
    """Azithromycin requires prescription -> require_prescription when no URL."""
    reload_master()
    nlu = _nlu_result("med_azithro_250", "Azithromycin 250mg", 10)
    out = evaluate(nlu, prescription_url=None)
    assert out["decision"] == "require_prescription"
    assert out["fulfill_qty"] == 0


def test_prescription_satisfied():
    """With prescription_url, rx medicine can be approved if in stock."""
    reload_master()
    nlu = _nlu_result("med_azithro_250", "Azithromycin 250mg", 10)
    out = evaluate(nlu, prescription_url="https://example.com/rx.pdf")
    assert out["decision"] == "auto_approve"
    assert out["fulfill_qty"] == 10


def test_auto_approve_otc():
    """Aspirin is OTC and in stock -> auto_approve."""
    reload_master()
    nlu = _nlu_result("med_aspirin_75", "Aspirin (75 mg)", 10)
    out = evaluate(nlu)
    assert out["decision"] == "auto_approve"
    assert out["fulfill_qty"] == 10


def test_low_stock_partial():
    """Request more than stock -> partial_fulfillment_and_procure."""
    reload_master()
    # Aspirin has 120; request 200
    nlu = _nlu_result("med_aspirin_75", "Aspirin (75 mg)", 200)
    out = evaluate(nlu)
    assert out["decision"] == "partial_fulfillment_and_procure"
    assert out["fulfill_qty"] == 120
    assert out["procure_qty"] == 80


def test_zero_stock():
    """Zero stock -> reject and procure."""
    reload_master()
    update_stock("med_aspirin_75", -120)  # drain
    nlu = _nlu_result("med_aspirin_75", "Aspirin (75 mg)", 10)
    out = evaluate(nlu)
    assert out["decision"] == "reject"
    assert out["fulfill_qty"] == 0
    assert out["procure_qty"] == 10
    # Restore for other tests
    update_stock("med_aspirin_75", 120)
