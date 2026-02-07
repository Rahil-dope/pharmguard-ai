"""
Simple deterministic refill predictor: average days between purchases per user/medicine,
estimate days_left from last purchase + qty and default 1 pill/day; alert when days_left <= threshold.
"""
from datetime import datetime, timedelta
from typing import Any

from app.utils import load_medicine_master, load_order_history
from app.db import SessionLocal
from app.models import Order

DEFAULT_DAYS_THRESHOLD = 7
DEFAULT_DOSES_PER_DAY = 1


def _parse_date(s: str) -> datetime | None:
    """Parse date from YYYY-MM-DD or similar."""
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _order_records_from_db(user_id: str) -> list[dict]:
    """Fetch order history for user from DB."""
    db = SessionLocal()
    try:
        rows = db.query(Order).filter(Order.user_id == user_id).order_by(Order.created_at.asc()).all()
        return [
            {
                "order_id": r.order_id,
                "medicine_id": r.medicine_id,
                "medicine_name": r.medicine_name,
                "qty": r.qty,
                "date": r.created_at.date().isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    finally:
        db.close()


def _order_records_from_csv(user_id: str) -> list[dict]:
    """Fetch from order_history.csv (fallback)."""
    rows = load_order_history()
    return [r for r in rows if r.get("user_id") == user_id]


def get_user_order_history(user_id: str) -> list[dict]:
    """Merge DB orders and CSV history for user, sorted by date."""
    from_db = _order_records_from_db(user_id)
    from_csv = _order_records_from_csv(user_id)
    combined = from_db + from_csv
    # Dedupe by order_id
    seen = set()
    unique = []
    for r in combined:
        oid = r.get("order_id")
        if oid and oid not in seen:
            seen.add(oid)
            unique.append(r)
    unique.sort(key=lambda x: (x.get("date") or ""))
    return unique


def estimate_days_between(orders: list[dict], medicine_id: str) -> float | None:
    """Average days between consecutive orders for this medicine."""
    med_orders = [o for o in orders if o.get("medicine_id") == medicine_id]
    if len(med_orders) < 2:
        return None
    dates = []
    for o in med_orders:
        d = _parse_date(o.get("date") or "")
        if d:
            dates.append(d)
    dates.sort()
    gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
    return sum(gaps) / len(gaps) if gaps else None


def estimate_days_left(
    last_order_date: str | None,
    last_qty: int,
    doses_per_day: float = DEFAULT_DOSES_PER_DAY,
) -> float | None:
    """Estimate days until runout: last_qty / doses_per_day from last_order_date."""
    if not last_order_date or last_qty <= 0:
        return None
    days_of_supply = last_qty / doses_per_day if doses_per_day else 0
    start = _parse_date(last_order_date)
    if not start:
        return None
    end = start + timedelta(days=days_of_supply)
    now = datetime.utcnow()
    if end <= now:
        return 0.0
    return (end - now).days


def get_refill_alerts(
    user_id: str,
    days_threshold: int = DEFAULT_DAYS_THRESHOLD,
    doses_per_day: float = DEFAULT_DOSES_PER_DAY,
) -> list[dict[str, Any]]:
    """
    For a user, compute refill alerts: medicines with days_left <= days_threshold.
    Returns list of {"user_id", "medicine_id", "medicine_name", "days_left", "last_order_date", "recommended_qty"}.
    """
    orders = get_user_order_history(user_id)
    if not orders:
        return []
    alerts = []
    # Group by medicine: last order and qty
    by_med: dict[str, list[dict]] = {}
    for o in orders:
        mid = o.get("medicine_id")
        if not mid:
            continue
        by_med.setdefault(mid, []).append(o)
    for medicine_id, med_orders in by_med.items():
        last = med_orders[-1]
        last_date = last.get("date")
        last_qty = int(last.get("qty") or 0)
        days_left = estimate_days_left(last_date, last_qty, doses_per_day)
        if days_left is None:
            continue
        if days_left <= days_threshold:
            avg_days = estimate_days_between(orders, medicine_id)
            recommended_qty = int(avg_days * doses_per_day) if avg_days else last_qty
            medicine_name = last.get("medicine_name") or medicine_id
            alerts.append({
                "user_id": user_id,
                "medicine_id": medicine_id,
                "medicine_name": medicine_name,
                "days_left": round(days_left, 1),
                "last_order_date": last_date,
                "recommended_qty": recommended_qty,
            })
    return alerts
