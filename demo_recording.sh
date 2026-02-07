#!/usr/bin/env bash
# Terminal curl demo for PharmGuard AI. Run with backend at http://localhost:8000.
set -e
BASE="${1:-http://localhost:8000}"
echo "=== PharmGuard AI curl demo (backend: $BASE) ==="
echo ""
echo "1. Health"
curl -s "$BASE/health" | head -1
echo ""
echo "2. Inventory (first 2 items)"
curl -s "$BASE/api/inventory?page_size=2" | python3 -m json.tool | head -25
echo ""
echo "3. Converse: Auto-approve (Aspirin OTC)"
curl -s -X POST "$BASE/api/converse" -H "Content-Type: application/json" \
  -d '{"user_id":"u100","text":"I need 5 Aspirin 75mg tablets","context":{}}' | python3 -m json.tool
echo ""
echo "4. Converse: Require prescription (Azithromycin)"
curl -s -X POST "$BASE/api/converse" -H "Content-Type: application/json" \
  -d '{"user_id":"u100","text":"I need Azithromycin 250mg","context":{}}' | python3 -m json.tool
echo ""
echo "5. User u100 refill alerts"
curl -s "$BASE/api/users/u100/alerts" | python3 -m json.tool
echo ""
echo "=== Demo done. Use trace_id from step 3 to GET /api/trace/<trace_id> ==="
