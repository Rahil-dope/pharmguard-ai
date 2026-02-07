"""
Pydantic schemas for API request/response validation.
"""
from typing import Optional, Any
from pydantic import BaseModel, Field


# --- Converse ---
class ConverseRequest(BaseModel):
    """Request body for POST /converse."""
    user_id: str = Field(..., description="User identifier")
    text: str = Field(..., description="User message")
    context: dict = Field(default_factory=dict, description="Optional context")


class ConverseResponse(BaseModel):
    """Response from POST /converse."""
    trace_id: str
    status: str = "ok"
    decision: str  # auto_approve | require_prescription | reject | partial_fulfillment_and_procure
    message: str
    order_id: Optional[str] = None
    prescription_required: Optional[bool] = None


# --- Orders ---
class OrderCreate(BaseModel):
    """Request body for POST /orders."""
    user_id: str
    medicine_id: str
    medicine_name: str
    qty: int = Field(..., ge=1)
    prescription_url: Optional[str] = None


class OrderResponse(BaseModel):
    """Order record returned by API."""
    order_id: str
    user_id: str
    medicine_id: str
    medicine_name: str
    qty: int
    prescription_url: Optional[str] = None
    status: str

    class Config:
        from_attributes = True


# --- Inventory ---
class MedicineItem(BaseModel):
    """Single medicine in inventory list."""
    id: str
    name: str
    brand: str
    unit: str
    stock: int
    prescription_required: bool
    unit_strength: Optional[str] = None


class InventoryListResponse(BaseModel):
    """Paginated inventory response."""
    items: list[MedicineItem]
    total: int
    page: int
    page_size: int


# --- Webhook ---
class FulfillmentWebhookPayload(BaseModel):
    """Payload for POST /webhook/fulfillment."""
    order_id: str


# --- Trace ---
class TraceResponse(BaseModel):
    """Trace content for GET /trace/{trace_id}."""
    trace_id: str
    trace: Any  # full trace object


# --- Alerts ---
class RefillAlert(BaseModel):
    """Proactive refill alert for a user."""
    user_id: str
    medicine_id: str
    medicine_name: str
    days_left: float
    last_order_date: Optional[str] = None
    recommended_qty: Optional[int] = None


class AlertsResponse(BaseModel):
    """Response for GET /users/{user_id}/alerts."""
    user_id: str
    alerts: list[RefillAlert]
