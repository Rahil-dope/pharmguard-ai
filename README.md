# PharmGuard AI

Agentic pharmacy system: conversational orders (text only), prescription & stock rules, predictive refill alerts, order creation with mock webhooks, and traceable chain-of-thought observability.

## Features

- **Conversational orders**: Natural language input → NLU (spaCy + rapidfuzz) → medicine slot filling; optional OpenAI disambiguation.
- **Safety engine**: Enforces `prescription_required` and stock rules; returns `auto_approve` / `require_prescription` / `reject` / `partial_fulfillment_and_procure`.
- **Refill predictor**: Simple deterministic refill alerts from order history (average days between purchases, days left).
- **Actions**: Creates orders in SQLite, decrements stock, triggers mock fulfillment webhook (background).
- **Observability**: Traces (CoT) in SQLite + `traces/{trace_id}.json`; optional Langfuse when `OBS_API_KEY` is set.
- **Admin UI**: Streamlit two-column: chat + Create order; admin panel (inventory, procurements, refill alerts, trace viewer).

## Quickstart

**One command (Docker Compose):**

```bash
docker-compose up --build
```

- Frontend: **http://localhost:8501**
- Backend API docs: **http://localhost:8000/docs**
- Health: **http://localhost:8000/health**

## Run locally (no Docker)

1. **Backend**

   ```bash
   cd pharmguard-ai
   pip install -r backend/requirements.txt
   # Optional: python -m spacy download en_core_web_sm
   set DATA_DIR=%cd%\data
   uvicorn app.main:app --reload --app-dir backend
   ```

   Or use the helper script (Unix/Git Bash):

   ```bash
   ./run_local.sh
   ```

   From project root, run backend as:

   ```bash
   pip install -r backend/requirements.txt
   cd backend && uvicorn app.main:app --reload
   ```

   Ensure `data/` is next to `backend/` (or set `DATA_DIR` to the folder containing `medicine_master.csv` and `order_history.csv`).

2. **Frontend**

   ```bash
   pip install -r frontend/requirements.txt
   cd frontend && streamlit run app.py
   ```

   Set `BACKEND_URL=http://localhost:8000` if needed.

## Environment variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Optional. Enables LLM disambiguation and CoT. |
| `OBS_API_KEY` | Optional. Sends traces to Langfuse/LangSmith. |
| `FULFILLMENT_WEBHOOK_URL` | Default: `http://localhost:8000/api/mock/warehouse`. |
| `ADMIN_TOKEN` | Shared token for admin panel (e.g. `demo-admin-token`). |
| `DATA_DIR` | Directory with `medicine_master.csv` and `order_history.csv`. |
| `SQLITE_DB_PATH` | SQLite file path for orders/traces. |

See `.env.example` for a template.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check. |
| GET | `/api/inventory` | Paginated inventory (from master + live stock). |
| GET | `/api/inventory/{medicine_id}` | Medicine detail. |
| GET | `/api/users/{user_id}/history` | Order history. |
| GET | `/api/users/{user_id}/alerts` | Refill alerts. |
| POST | `/api/converse` | Conversational order (JSON: `user_id`, `text`, `context`). |
| POST | `/api/orders` | Create order directly (with optional `prescription_url`). |
| POST | `/api/webhook/fulfillment` | Fulfillment webhook (order_id). |
| POST | `/api/mock/warehouse` | Mock warehouse (echo payload). |
| GET | `/api/trace/{trace_id}` | Get full CoT trace. |
| GET | `/api/procurements` | Pending procurements (admin). |

## Demo script (3 scenarios)

### 1. Auto-approve (OTC)

- In Streamlit chat, User ID: `u100`, message: **"I need 10 Aspirin 75mg tablets"**.
- Expected: decision `auto_approve`, order created, trace_id returned.
- Or: `curl -X POST http://localhost:8000/api/converse -H "Content-Type: application/json" -d "{\"user_id\":\"u100\",\"text\":\"I need 10 Aspirin 75mg tablets\",\"context\":{}}"`

### 2. Prescription required

- Message: **"I need Azithromycin 250mg"**.
- Expected: decision `require_prescription`, message to upload prescription.
- Then use "Create order directly" with Medicine ID `med_azithro_250`, Prescription URL `https://example.com/rx.pdf`, or send another `/converse` with `context: {"prescription_url": "https://example.com/rx.pdf"}`.

### 3. Proactive refill alert

- User `u100` has history in `data/order_history.csv` (Losartan, Metformin).
- Open Admin panel → Refill alerts → User for alerts: `u100` → Load alerts.
- Expected: alerts for medicines with `days_left <= 7` (depending on dates and qty).

## Trace link for judges

- **With OBS_API_KEY**: Use the public Langfuse/LangSmith link you configure.
- **Without**: After a conversation, copy the `trace_id` from the response and open:
  - **http://localhost:8000/api/trace/{trace_id}** (JSON).
  - Or open the file **`traces/{trace_id}.json`** in the project (when running locally; traces dir is created next to the process).

## Tests

From project root:

```bash
pip install -r backend/requirements.txt
pip install pytest httpx
set PYTHONPATH=backend
pytest tests -v
```

Or from repo root (e.g. in CI):

```bash
cd pharmguard-ai
$env:PYTHONPATH = "backend"
pytest tests -v
```

## Submission checklist

- [ ] Public GitHub repo
- [ ] README with run instructions
- [ ] Live observability link (if `OBS_API_KEY` set) or instructions for `GET /api/trace/{id}`
- [ ] Sample dataset in `data/`

## License

MIT (see LICENSE).
