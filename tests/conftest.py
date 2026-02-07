"""
Pytest configuration: add backend to path and set DATA_DIR for tests.
"""
import os
import sys
from pathlib import Path

# Project root = parent of tests/
ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
DATA = ROOT / "data"
sys.path.insert(0, str(BACKEND))
os.environ["DATA_DIR"] = str(DATA)
# Use a test DB
os.environ["SQLITE_DB_PATH"] = str(ROOT / "data" / "test_pharmguard.db")
