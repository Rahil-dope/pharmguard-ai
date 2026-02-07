"""
PharmGuard AI - Streamlit frontend.
Two-column: left = chat (POST /converse), right = admin (inventory, procurements, alerts, trace viewer).
"""
import os
import streamlit as st
import requests

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "demo-admin-token")
DEFAULT_USER = "u100"


def api_get(path: str, token: str | None = None):
    headers = {}
    if token:
        headers["X-Admin-Token"] = token
    r = requests.get(f"{BACKEND_URL}{path}", headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()


def api_post(path: str, json: dict):
    r = requests.post(f"{BACKEND_URL}{path}", json=json, timeout=10)
    r.raise_for_status()
    return r.json()


st.set_page_config(page_title="PharmGuard AI", layout="wide")
st.title("PharmGuard AI")

col_chat, col_admin = st.columns([1, 1])

with col_chat:
    st.subheader("Chat")
    user_id = st.text_input("User ID", value=DEFAULT_USER, key="user_id")
    text = st.text_input("Your message", placeholder="e.g. I need 10 Aspirin 75mg tablets", key="msg")
    prescription_url = st.text_input("Prescription URL (if required)", placeholder="https://...", key="rx_url")

    if st.button("Send"):
        if not text.strip():
            st.warning("Enter a message.")
        else:
            context = {}
            if prescription_url.strip():
                context["prescription_url"] = prescription_url.strip()
            try:
                out = api_post("/api/converse", {
                    "user_id": user_id,
                    "text": text.strip(),
                    "context": context,
                })
                st.success(out.get("message", ""))
                st.json({
                    "decision": out.get("decision"),
                    "order_id": out.get("order_id"),
                    "trace_id": out.get("trace_id"),
                })
                if out.get("prescription_required"):
                    st.info("Upload prescription and submit again with Prescription URL, or use Create Order below.")
            except requests.exceptions.RequestException as e:
                st.error(f"Request failed: {e}")

    st.subheader("Create order directly")
    with st.form("order_form"):
        o_user = st.text_input("User ID", value=DEFAULT_USER, key="o_user")
        o_med_id = st.text_input("Medicine ID", value="med_aspirin_75", key="o_med_id")
        o_med_name = st.text_input("Medicine name", value="Aspirin (75 mg)", key="o_med_name")
        o_qty = st.number_input("Qty", min_value=1, value=10, key="o_qty")
        o_rx = st.text_input("Prescription URL (optional)", key="o_rx")
        if st.form_submit_button("Create order"):
            try:
                payload = {"user_id": o_user, "medicine_id": o_med_id, "medicine_name": o_med_name, "qty": o_qty}
                if o_rx.strip():
                    payload["prescription_url"] = o_rx.strip()
                out = api_post("/api/orders", payload)
                st.success(f"Order created: {out.get('order_id')}")
            except requests.exceptions.RequestException as e:
                st.error(str(e))

with col_admin:
    st.subheader("Admin")
    admin_token = st.text_input("Admin token", value=ADMIN_TOKEN, type="password", key="admin_token")
    if not admin_token or admin_token != ADMIN_TOKEN:
        st.warning("Set ADMIN_TOKEN in env to access admin panel.")
    else:
        try:
            inv = api_get("/api/inventory")
            st.write("**Inventory**")
            st.dataframe(inv.get("items", [])[:20], use_container_width=True)
        except Exception as e:
            st.caption(f"Inventory: {e}")

        try:
            proc = api_get("/api/procurements", token=admin_token)
            st.write("**Pending procurements**")
            st.json(proc.get("procurements", []))
        except Exception as e:
            st.caption(f"Procurements: {e}")

        st.write("**Refill alerts**")
        alert_user = st.text_input("User for alerts", value=DEFAULT_USER, key="alert_user")
        if st.button("Load alerts"):
            try:
                alerts = api_get(f"/api/users/{alert_user}/alerts")
                st.json(alerts.get("alerts", []))
            except Exception as e:
                st.caption(str(e))

        st.write("**Trace viewer**")
        trace_id = st.text_input("Trace ID", placeholder="tr_...", key="trace_id")
        if st.button("Load trace"):
            if trace_id.strip():
                try:
                    t = api_get(f"/api/trace/{trace_id.strip()}")
                    st.json(t.get("trace", t))
                except Exception as e:
                    st.error(str(e))
            else:
                st.warning("Enter a trace ID.")
