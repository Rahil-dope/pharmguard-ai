"""
SQLAlchemy models for orders, traces, inventory snapshots, fulfillment and procurement logs.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.db import Base


class Order(Base):
    """Order record persisted to SQLite."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    medicine_id = Column(String(128), nullable=False)
    medicine_name = Column(String(256), nullable=False)
    qty = Column(Integer, nullable=False)
    prescription_url = Column(String(512), nullable=True)
    status = Column(String(32), default="created")
    created_at = Column(DateTime, default=datetime.utcnow)


class Trace(Base):
    """Chain-of-thought trace stored for observability."""
    __tablename__ = "traces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trace_id = Column(String(64), unique=True, nullable=False, index=True)
    trace_json = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)


class InventorySnapshot(Base):
    """Snapshot of medicine stock after orders (for live inventory view)."""
    __tablename__ = "inventory_snapshot"

    id = Column(Integer, primary_key=True, autoincrement=True)
    medicine_id = Column(String(128), nullable=False, unique=True, index=True)
    stock = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FulfillmentLog(Base):
    """Log of webhook fulfillment responses."""
    __tablename__ = "fulfillment_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(64), nullable=False, index=True)
    response_status = Column(Integer, default=200)
    response_body = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProcurementLog(Base):
    """Log of procurement webhook calls (simulated)."""
    __tablename__ = "procurement_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    medicine_id = Column(String(128), nullable=False, index=True)
    qty_requested = Column(Integer, nullable=False)
    status = Column(String(32), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
