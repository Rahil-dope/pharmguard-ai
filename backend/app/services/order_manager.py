"""
Order Manager: create and persist orders to SQLite, decrement in-memory stock,
persist inventory_snapshot, and trigger background webhook to fulfillment.
"""
import logging
from typing import Optional

from app.db import SessionLocal
from app.models import Order, InventorySnapshot, FulfillmentLog, ProcurementLog
from app.utils import generate_order_id
from app.services.safety_engine import update_stock, get_medicine

logger = logging.getLogger(__name__)


def log_procurement(medicine_id: str, qty_requested: int) -> None:
    """Persist procurement request to DB."""
    db = SessionLocal()
    try:
        log = ProcurementLog(medicine_id=medicine_id, qty_requested=qty_requested, status="pending")
        db.add(log)
        db.commit()
    finally:
        db.close()


def create_order(
    user_id: str,
    medicine_id: str,
    medicine_name: str,
    qty: int,
    prescription_url: Optional[str] = None,
) -> dict:
    """
    Create order in DB, decrement in-memory stock, update inventory_snapshot.
    Returns order record dict. Does NOT call webhook (caller uses BackgroundTasks).
    """
    order_id = generate_order_id()
    db = SessionLocal()
    try:
        order = Order(
            order_id=order_id,
            user_id=user_id,
            medicine_id=medicine_id,
            medicine_name=medicine_name,
            qty=qty,
            prescription_url=prescription_url,
            status="created",
        )
        db.add(order)
        update_stock(medicine_id, -qty)
        # Update or insert inventory_snapshot
        snap = db.query(InventorySnapshot).filter(InventorySnapshot.medicine_id == medicine_id).first()
        med = get_medicine(medicine_id)
        new_stock = (med["stock"] if med else 0)
        if snap:
            snap.stock = new_stock
        else:
            snap = InventorySnapshot(medicine_id=medicine_id, stock=new_stock)
            db.add(snap)
        db.commit()
        db.refresh(order)
        return {
            "order_id": order.order_id,
            "user_id": order.user_id,
            "medicine_id": order.medicine_id,
            "medicine_name": order.medicine_name,
            "qty": order.qty,
            "prescription_url": order.prescription_url,
            "status": order.status,
        }
    finally:
        db.close()


def log_fulfillment_response(order_id: str, status_code: int, body: str) -> None:
    """Persist webhook response to fulfillment_log."""
    db = SessionLocal()
    try:
        log = FulfillmentLog(order_id=order_id, response_status=status_code, response_body=body)
        db.add(log)
        db.commit()
    finally:
        db.close()


def get_pending_procurements() -> list[dict]:
    """Return list of pending procurement log entries for admin UI."""
    db = SessionLocal()
    try:
        rows = db.query(ProcurementLog).filter(ProcurementLog.status == "pending").order_by(ProcurementLog.created_at.desc()).limit(50).all()
        return [{"id": r.id, "medicine_id": r.medicine_id, "qty_requested": r.qty_requested, "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]
    finally:
        db.close()
