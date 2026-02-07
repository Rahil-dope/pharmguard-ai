"""
Observability: log traces to SQLite, to traces/{trace_id}.json, and optionally to Langfuse/LangSmith.
"""
import json
import logging
import os
from pathlib import Path
from typing import Any
from datetime import datetime

from app.db import SessionLocal
from app.models import Trace

logger = logging.getLogger(__name__)

OBS_API_KEY = os.environ.get("OBS_API_KEY")
TRACES_DIR = Path(os.environ.get("TRACES_DIR", "traces"))


def _ensure_traces_dir():
    TRACES_DIR.mkdir(parents=True, exist_ok=True)


def _send_to_langfuse(trace_id: str, trace_obj: dict) -> None:
    """If OBS_API_KEY set, POST trace to Langfuse (optional)."""
    if not OBS_API_KEY:
        return
    try:
        import httpx
        # Langfuse ingest endpoint (example; adjust to actual Langfuse API)
        url = os.environ.get("LANGFUSE_URL", "https://cloud.langfuse.com/api/public/ingestion")
        payload = {"trace_id": trace_id, "trace": trace_obj}
        resp = httpx.post(url, json=payload, headers={"Authorization": f"Bearer {OBS_API_KEY}"}, timeout=5.0)
        if resp.status_code >= 400:
            logger.warning("langfuse_ingest_failed", extra={"status": resp.status_code, "body": resp.text[:200]})
    except Exception as e:
        logger.warning("langfuse_ingest_error", extra={"error": str(e)})


def log_trace(trace_id: str, trace_obj: dict) -> None:
    """
    Persist trace: SQLite traces table, traces/{trace_id}.json file, and optional Langfuse.
    trace_obj should include: trace_id, timestamp, user_id, input_text, nlu_slots, safety_decision, action_taken, llm_cot.
    """
    if "timestamp" not in trace_obj:
        trace_obj["timestamp"] = datetime.utcnow().isoformat()
    trace_obj["trace_id"] = trace_id
    json_str = json.dumps(trace_obj, default=str)
    # SQLite
    db = SessionLocal()
    try:
        row = Trace(trace_id=trace_id, trace_json=json_str)
        db.add(row)
        db.commit()
    finally:
        db.close()
    # File
    _ensure_traces_dir()
    path = TRACES_DIR / f"{trace_id}.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(trace_obj, f, indent=2, default=str)
    except Exception as e:
        logger.warning("trace_file_write_failed", extra={"path": str(path), "error": str(e)})
    # Optional Langfuse
    _send_to_langfuse(trace_id, trace_obj)
    logger.info("trace_logged", extra={"trace_id": trace_id})


def get_trace(trace_id: str) -> dict | None:
    """Load trace from DB. Returns trace dict or None."""
    db = SessionLocal()
    try:
        row = db.query(Trace).filter(Trace.trace_id == trace_id).first()
        if not row or not row.trace_json:
            return None
        return json.loads(row.trace_json)
    finally:
        db.close()
