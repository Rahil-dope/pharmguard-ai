"""
Database setup for PharmGuard AI.
Uses SQLAlchemy with SQLite for orders, traces, inventory snapshots, and fulfillment log.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Default DB path: project root / data directory sibling
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = os.environ.get("SQLITE_DB_PATH", str(BASE_DIR / "data" / "pharmguard.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=os.environ.get("SQL_ECHO", "").lower() == "true",
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Call at app startup."""
    from app.models import Order, Trace, InventorySnapshot, FulfillmentLog, ProcurementLog  # noqa: F401
    Base.metadata.create_all(bind=engine)
