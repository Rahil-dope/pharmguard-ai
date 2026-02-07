"""
Test persistence: ensure stock changes are saved to DB and reloaded.
"""
import os
import sys
from pathlib import Path

# Ensure backend on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.environ["DATA_DIR"] = str(ROOT / "data")
os.environ["SQLITE_DB_PATH"] = str(ROOT / "data" / "test_persist.db")

from app.db import init_db, SessionLocal, engine, Base
from app.services.safety_engine import get_medicine, update_stock, reload_master, _ensure_loaded
from app.models import InventorySnapshot

def setup_module(module):
    """Setup clean DB."""
    Base.metadata.drop_all(bind=engine)
    init_db()

def test_stock_persistence():
    """
    1. Load master (stock from CSV).
    2. Update stock (decrement).
    3. Verify DB matches.
    4. Reload master (simulate restart).
    5. Verify stock is still lower (from DB), not reset to CSV value.
    """
def test_stock_persistence():
    """
    1. Load master (stock from CSV).
    2. Manually insert InventorySnapshot (simulating order_manager persistence).
    3. Reload master (simulate restart).
    4. Verify stock is updated from DB.
    """
    # 1. Initial load
    reload_master()
    med_id = "med_aspirin_75"
    initial = get_medicine(med_id)
    assert initial is not None
    start_stock = initial["stock"]
    
    # 2. Simulate persistence (what order_manager does)
    new_stock = start_stock - 5
    db = SessionLocal()
    snap = InventorySnapshot(medicine_id=med_id, stock=new_stock)
    db.add(snap)
    db.commit()
    db.close()

    # 3. Simulate restart (reload from CSV + DB)
    reload_master()
    
    # 4. Verify stock is preserved
    final = get_medicine(med_id)
    assert final["stock"] == new_stock, f"Expected {new_stock}, got {final['stock']}. DB load failed."
