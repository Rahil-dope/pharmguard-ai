"""
Safety Engine: checks prescription_required and stock for an NLU result.
Returns decision: auto_approve | require_prescription | reject | partial_fulfillment_and_procure.
Simulates trigger_procure (enqueue procurement webhook).
"""
import os
import logging
from typing import Any, Optional

from app.utils import load_medicine_master

logger = logging.getLogger(__name__)

# In-memory copy of medicine master with current stock (updated by order_manager)
_medicine_cache: dict[str, dict] = {}
_initialized = False


def _ensure_loaded():
    global _medicine_cache, _initialized
    if not _initialized:
        # 1. Load from CSV (Master)
        for row in load_medicine_master():
            _medicine_cache[row["id"]] = dict(row)

        # 2. Update from DB (Snapshot) - Persistence Fix
        try:
            from app.db import SessionLocal
            from app.models import InventorySnapshot
            
            db = SessionLocal()
            try:
                snapshots = db.query(InventorySnapshot).all()
                for snap in snapshots:
                    if snap.medicine_id in _medicine_cache:
                        _medicine_cache[snap.medicine_id]["stock"] = snap.stock
            except Exception as e:
                logger.error(f"Failed to load inventory snapshot from DB: {e}")
            finally:
                db.close()
        except ImportError:
            logger.warning("Could not import DB modules in safety_engine (likely during tests without DB setup).")

        _initialized = True


def get_medicine(medicine_id: str) -> Optional[dict]:
    """Get medicine by id from cache (stock may be updated)."""
    _ensure_loaded()
    return _medicine_cache.get(medicine_id)


def update_stock(medicine_id: str, delta: int) -> None:
    """Decrement (or update) stock in cache. Called by order_manager."""
    _ensure_loaded()
    if medicine_id in _medicine_cache:
        _medicine_cache[medicine_id]["stock"] = max(0, _medicine_cache[medicine_id]["stock"] + delta)


def get_all_medicines() -> list[dict]:
    """Return list of all medicines (current stock)."""
    _ensure_loaded()
    return list(_medicine_cache.values())


def reload_master() -> None:
    """Reload from CSV (e.g. after external update)."""
    global _medicine_cache, _initialized
    _medicine_cache = {}
    _initialized = False
    _ensure_loaded()


def trigger_procure(medicine_id: str, qty: int) -> None:
    """
    Simulate procurement: enqueue a webhook call or log.
    In this implementation we log and optionally POST to a procurement URL if set.
    """
    logger.info("procurement_triggered", extra={"medicine_id": medicine_id, "qty": qty})
    # Persist to DB via order_manager or a small helper when called from route
    from app.services.order_manager import log_procurement
    log_procurement(medicine_id, qty)


def evaluate(
    nlu_result: dict,
    prescription_url: Optional[str] = None,
    stock_override: Optional[dict[str, int]] = None,
) -> dict[str, Any]:
    """
    Evaluate NLU result against prescription and stock rules.
    Returns: {
      "decision": "auto_approve" | "require_prescription" | "reject" | "partial_fulfillment_and_procure",
      "message": str,
      "fulfill_qty": int (how many to fulfill now),
      "procure_qty": int (how many to procure),
      "medicine": dict or None
    }
    """
    _ensure_loaded()
    candidate = nlu_result.get("medicine_candidate")
    quantity = nlu_result.get("quantity") or 1
    if not candidate or not candidate.get("id"):
        return {
            "decision": "reject",
            "message": "Could not identify the medicine. Please specify the name or brand.",
            "fulfill_qty": 0,
            "procure_qty": 0,
            "medicine": None,
        }
    med_id = candidate["id"]
    medicine = _medicine_cache.get(med_id)
    if not medicine:
        return {
            "decision": "reject",
            "message": f"Medicine {med_id} not found in catalog.",
            "fulfill_qty": 0,
            "procure_qty": 0,
            "medicine": None,
        }
    stock = stock_override.get(med_id, medicine["stock"]) if stock_override else medicine["stock"]
    rx_required = medicine.get("prescription_required", False)
    if rx_required and not prescription_url:
        return {
            "decision": "require_prescription",
            "message": f"{medicine.get('name')} requires a prescription. Please upload or provide prescription.",
            "fulfill_qty": 0,
            "procure_qty": 0,
            "medicine": medicine,
        }
    if stock <= 0:
        trigger_procure(med_id, quantity)
        return {
            "decision": "reject",
            "message": f"{medicine.get('name')} is out of stock. We have triggered procurement.",
            "fulfill_qty": 0,
            "procure_qty": quantity,
            "medicine": medicine,
        }
    if stock >= quantity:
        return {
            "decision": "auto_approve",
            "message": f"Approved: {quantity} x {medicine.get('name')}.",
            "fulfill_qty": quantity,
            "procure_qty": 0,
            "medicine": medicine,
        }
    # stock < quantity and stock > 0
    shortfall = quantity - stock
    trigger_procure(med_id, shortfall)
    return {
        "decision": "partial_fulfillment_and_procure",
        "message": f"Partial: fulfilling {stock} now; {shortfall} will be procured.",
        "fulfill_qty": stock,
        "procure_qty": shortfall,
        "medicine": medicine,
    }
