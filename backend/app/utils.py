"""
Utility functions: CSV loading, path resolution, ID generation.
"""
import csv
import os
import uuid
from pathlib import Path
from typing import Any

# utils.py lives in backend/app/; project root = pharmguard-ai (parent of backend)
APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"


def get_data_dir() -> Path:
    """Return data directory; prefer env override."""
    return Path(os.environ.get("DATA_DIR", str(DATA_DIR)))


def load_csv(path: Path, required: bool = True) -> list[dict[str, Any]]:
    """
    Load a CSV file and return list of row dicts.
    Returns [] if file missing and not required.
    """
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Required data file not found: {path}")
        return []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_medicine_master() -> list[dict[str, Any]]:
    """Load medicine_master.csv from data dir."""
    data_dir = get_data_dir()
    path = data_dir / "medicine_master.csv"
    rows = load_csv(path, required=True)
    # Normalize types
    for r in rows:
        r["stock"] = int(r.get("stock", 0))
        r["prescription_required"] = str(r.get("prescription_required", "false")).lower() == "true"
    return rows


def load_order_history() -> list[dict[str, Any]]:
    """Load order_history.csv from data dir (fallback history)."""
    data_dir = get_data_dir()
    path = data_dir / "order_history.csv"
    return load_csv(path, required=False)


def generate_trace_id() -> str:
    """Generate a unique trace ID."""
    return f"tr_{uuid.uuid4().hex[:16]}"


def generate_order_id() -> str:
    """Generate a unique order ID."""
    return f"ord_{uuid.uuid4().hex[:12]}"
