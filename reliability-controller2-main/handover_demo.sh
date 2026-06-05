#!/bin/bash
# ============================================================
# PRAVAH — HANDOVER DEMO SCRIPT
# Run this script to see a complete end-to-end trace in action
# Requirements: curl, uuidgen
# ============================================================

set -e

SERVER="54.156.236.10"
WEB1="http://$SERVER:30001"
SARATHI="http://$SERVER:30005"
STREAM="http://$SERVER/signals/stream"

echo ""
echo "============================================================"
echo " PRAVAH — FULL TRACE DEMO"
echo "============================================================"
echo ""

# Step 0 — Health check
echo "[0] Health checks..."
curl -s http://$SERVER/health | python3 -m json.tool
echo ""

# Step 1 — Generate trace_id
TRACE=$(uuidgen)
echo "[1] trace_id generated (Core): $TRACE"
echo ""

# Step 2 — Open stream in background, capture to file
STREAM_FILE=$(mktemp)
echo "[2] Opening stream..."
curl -s -H "Host: pravah.blackholeinfiverse.com" \
  -N "$STREAM" > "$STREAM_FILE" &
STREAM_PID=$!
sleep 1
echo "    Stream open (PID $STREAM_PID)"
echo ""

# Step 3 — Login (Core → Monitor)
echo "[3] Login (Core)..."
curl -s -X POST "$WEB1/login" \
  -H "X-TRACE-ID: $TRACE" \
  -d "user_id=demo_user" > /dev/null
echo "    Login done"
echo ""

# Step 4 — Click (Core → Monitor)
echo "[4] Click (Core)..."
curl -s -X POST "$WEB1/click" \
  -H "X-TRACE-ID: $TRACE" \
  -d "user_id=demo_user&session_id=s_demo" > /dev/null
echo "    Click done"
echo ""

# Step 5 — Decision (Sarathi → Monitor → Executer → Monitor)
echo "[5] Decision (Sarathi)..."
RESPONSE=$(curl -s -X POST "$SARATHI/decision" \
  -H "Content-Type: application/json" \
  -d "{
    \"trace_id\": \"$TRACE\",
    \"service_id\": \"web1-blue\",
    \"action_type\": \"restart\",
    \"payload\": {\"decision_score\": 0.9}
  }")
echo "    Response: $RESPONSE"
echo ""

# Wait for stream to capture all signals
sleep 2

# Step 6 — Stop stream and show signals for this trace
echo "[6] Stream signals for trace $TRACE:"
echo "------------------------------------------------------------"
kill $STREAM_PID 2>/dev/null || true
grep "$TRACE" "$STREAM_FILE" | while read -r line; do
  echo "$line" | sed 's/^data: //' | python3 -m json.tool 2>/dev/null || echo "$line"
  echo "---"
done
rm -f "$STREAM_FILE"

echo ""
echo "============================================================"
echo " DEMO COMPLETE"
echo "============================================================"
echo ""
echo "Expected signals in order:"
echo "  1. login_detected"
echo "  2. user_interaction (page_view)"
echo "  3. user_interaction (click)"
echo "  4. decision (ALLOW)"
echo "  5. enforcement (validated)"
echo "  6. execution (RUNNING)"
echo "  7. verification (SUCCESS)"
echo "  8. execution_completed"
echo ""
echo "If all 8 appeared — system is fully operational."