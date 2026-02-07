"""
API routes: inventory, user history, converse, orders, trace, alerts.
"""
import os
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.security import APIKeyHeader

from app.schema import (
    ConverseRequest,
    ConverseResponse,
    OrderCreate,
    OrderResponse,
    MedicineItem,
    InventoryListResponse,
    TraceResponse,
    RefillAlert,
    AlertsResponse,
)
from app.services.nlu import run_nlu
from app.services.safety_engine import evaluate, get_medicine, get_all_medicines
from app.services.order_manager import create_order, log_fulfillment_response, get_pending_procurements
from app.services.predictor import get_refill_alerts, get_user_order_history
from app.services.observability import log_trace, get_trace
from app.services.llm_client import chain_of_thought
from app.utils import generate_trace_id
from app.db import SessionLocal
from app.models import Order, InventorySnapshot

logger = logging.getLogger(__name__)
router = APIRouter()

# Optional: secure admin endpoints with header
ADMIN_HEADER = APIKeyHeader(name="X-Admin-Token", auto_error=False)


def _current_stock(medicine_id: str) -> int:
    """Get current stock: from safety engine cache (already updated by orders)."""
    med = get_medicine(medicine_id)
    return med["stock"] if med else 0


@router.get("/inventory", response_model=InventoryListResponse)
def list_inventory(page: int = 1, page_size: int = 50):
    """Paginated list of medicines from master + live stock from DB/cache."""
    all_meds = get_all_medicines()
    total = len(all_meds)
    start = (page - 1) * page_size
    slice_meds = all_meds[start : start + page_size]
    items = [
        MedicineItem(
            id=m["id"],
            name=m["name"],
            brand=m["brand"],
            unit=m["unit"],
            stock=m["stock"],
            prescription_required=m["prescription_required"],
            unit_strength=m.get("unit_strength"),
        )
        for m in slice_meds
    ]
    return InventoryListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/inventory/{medicine_id}", response_model=MedicineItem)
def get_inventory_item(medicine_id: str):
    """Medicine detail by id."""
    med = get_medicine(medicine_id)
    if not med:
        raise HTTPException(status_code=404, detail="Medicine not found")
    return MedicineItem(
        id=med["id"],
        name=med["name"],
        brand=med["brand"],
        unit=med["unit"],
        stock=med["stock"],
        prescription_required=med["prescription_required"],
        unit_strength=med.get("unit_strength"),
    )


@router.get("/users/{user_id}/history")
def user_history(user_id: str):
    """Order history for user (DB + CSV fallback)."""
    history = get_user_order_history(user_id)
    return {"user_id": user_id, "orders": history}


@router.get("/users/{user_id}/alerts", response_model=AlertsResponse)
def user_alerts(user_id: str):
    """Proactive refill alerts for user."""
    alerts = get_refill_alerts(user_id)
    return AlertsResponse(user_id=user_id, alerts=[RefillAlert(**a) for a in alerts])


def _call_fulfillment_webhook(order_id: str) -> None:
    """Background task: POST to fulfillment webhook and log response."""
    import httpx
    url = os.environ.get("FULFILLMENT_WEBHOOK_URL", "http://localhost:8000/api/webhook/fulfillment")
    try:
        resp = httpx.post(url, json={"order_id": order_id}, timeout=10.0)
        log_fulfillment_response(order_id, resp.status_code, resp.text[:500])
    except Exception as e:
        log_fulfillment_response(order_id, 0, str(e))


@router.post("/converse", response_model=ConverseResponse)
def converse(req: ConverseRequest, background_tasks: BackgroundTasks):
    """
    Conversational order: NLU -> Safety -> create order (if approved) -> background webhook -> trace.
    """
    trace_id = generate_trace_id()
    prescription_url = (req.context or {}).get("prescription_url")
    nlu_result = run_nlu(req.text)
    safety_result = evaluate(nlu_result, prescription_url=prescription_url)
    decision = safety_result["decision"]
    message = safety_result["message"]
    order_id = None
    status = "ok"
    medicine = safety_result.get("medicine")
    action_taken = "none"
    fulfill_qty = safety_result.get("fulfill_qty", 0)

    if decision == "auto_approve" or decision == "partial_fulfillment_and_procure":
        if medicine and fulfill_qty > 0:
            order_record = create_order(
                user_id=req.user_id,
                medicine_id=medicine["id"],
                medicine_name=medicine["name"],
                qty=fulfill_qty,
                prescription_url=prescription_url,
            )
            order_id = order_record["order_id"]
            action_taken = f"order_created:{order_id}"
            background_tasks.add_task(_call_fulfillment_webhook, order_id)

    cot = chain_of_thought(
        req.text,
        nlu_result.get("raw_slots", {}),
        decision,
        action_taken,
    )
    trace_obj = {
        "trace_id": trace_id,
        "user_id": req.user_id,
        "input_text": req.text,
        "nlu_slots": nlu_result,
        "safety_decision": decision,
        "safety_message": message,
        "action_taken": action_taken,
        "order_id": order_id,
        "llm_cot": cot,
    }
    log_trace(trace_id, trace_obj)

    return ConverseResponse(
        trace_id=trace_id,
        status=status,
        decision=decision,
        message=message,
        order_id=order_id,
        prescription_required=(decision == "require_prescription"),
    )


@router.post("/orders", response_model=OrderResponse)
def create_order_endpoint(req: OrderCreate, background_tasks: BackgroundTasks):
    """Create order directly; accepts prescription_url. Triggers fulfillment webhook."""
    safety_result = evaluate(
        {"medicine_candidate": {"id": req.medicine_id, "name": req.medicine_name}, "quantity": req.qty},
        prescription_url=req.prescription_url,
    )
    if safety_result["decision"] not in ("auto_approve", "partial_fulfillment_and_procure"):
        raise HTTPException(
            status_code=400,
            detail=safety_result["message"] or "Order not approved (prescription or stock).",
        )
    fulfill_qty = safety_result.get("fulfill_qty", 0)
    if fulfill_qty <= 0:
        raise HTTPException(status_code=400, detail="Cannot fulfill: out of stock.")
    order_record = create_order(
        user_id=req.user_id,
        medicine_id=req.medicine_id,
        medicine_name=req.medicine_name,
        qty=fulfill_qty,
        prescription_url=req.prescription_url,
    )
    background_tasks.add_task(_call_fulfillment_webhook, order_record["order_id"])
    return OrderResponse(**order_record)


@router.get("/trace/{trace_id}", response_model=TraceResponse)
def get_trace_endpoint(trace_id: str):
    """Return full CoT trace for given trace_id."""
    trace = get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return TraceResponse(trace_id=trace_id, trace=trace)


@router.get("/procurements")
def list_procurements(token: Optional[str] = Depends(ADMIN_HEADER)):
    """Pending procurements for admin UI (optional admin token)."""
    return {"procurements": get_pending_procurements()}
