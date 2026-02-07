"""
Webhook endpoints: fulfillment (simulated) and mock warehouse.
"""
from fastapi import APIRouter
from pydantic import BaseModel
import logging

from app.services.order_manager import log_fulfillment_response

logger = logging.getLogger(__name__)
router = APIRouter()


class FulfillmentPayload(BaseModel):
    order_id: str


@router.post("/webhook/fulfillment")
def fulfillment_webhook(payload: FulfillmentPayload):
    """
    Simulate fulfillment system: accept order_id, return success, write to fulfillment_log.
    """
    order_id = payload.order_id
    log_fulfillment_response(order_id, 200, '{"status":"fulfilled"}')
    logger.info("fulfillment_received", extra={"order_id": order_id})
    return {"status": "ok", "order_id": order_id}


@router.post("/mock/warehouse")
def mock_warehouse(payload: dict):
    """
    Mock warehouse endpoint: print payload and respond success.
    Used as default FULFILLMENT_WEBHOOK_URL for demos.
    """
    logger.info("mock_warehouse_received", extra={"payload": payload})
    print("[MOCK WAREHOUSE]", payload)
    return {"status": "success", "received": payload}
