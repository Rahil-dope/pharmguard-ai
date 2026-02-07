"""
End-to-end test: TestClient converse -> order -> webhook flow.
"""
import os
import sys
from pathlib import Path

# Ensure backend on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.environ["DATA_DIR"] = str(ROOT / "data")
os.environ["SQLITE_DB_PATH"] = str(ROOT / "data" / "test_e2e.db")

from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db

# Init DB before tests
init_db()

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_inventory():
    r = client.get("/api/inventory")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert data["total"] >= 4
    ids = [m["id"] for m in data["items"]]
    assert "med_aspirin_75" in ids


def test_converse_auto_approve():
    """Converse with Aspirin (OTC) -> auto_approve and order created."""
    r = client.post("/api/converse", json={
        "user_id": "u_test",
        "text": "I need 5 Aspirin 75mg tablets",
        "context": {},
    })
    assert r.status_code == 200
    data = r.json()
    assert data["decision"] == "auto_approve"
    assert data.get("order_id") is not None
    assert data.get("trace_id") is not None


def test_converse_require_prescription():
    """Ask for Azithromycin without prescription -> require_prescription."""
    r = client.post("/api/converse", json={
        "user_id": "u_test",
        "text": "I need Azithromycin 250mg",
        "context": {},
    })
    assert r.status_code == 200
    data = r.json()
    assert data["decision"] == "require_prescription"
    assert data.get("prescription_required") is True


def test_webhook_fulfillment():
    """POST to webhook/fulfillment returns success."""
    r = client.post("/api/webhook/fulfillment", json={"order_id": "ord_test123"})
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_trace_get():
    """Converse then GET trace."""
    conv = client.post("/api/converse", json={
        "user_id": "u_trace",
        "text": "2 Aspirin",
        "context": {},
    })
    assert conv.status_code == 200
    trace_id = conv.json().get("trace_id")
    if trace_id:
        r = client.get(f"/api/trace/{trace_id}")
        assert r.status_code == 200
        t = r.json().get("trace") or r.json()
        assert t.get("trace_id") == trace_id
        assert "input_text" in t or "nlu_slots" in t
