# HANDOVER_FAQ.md

15 real questions a new developer will ask, with direct answers.

---

**Q1. Where is trace_id generated?**

In the caller — whoever sends the HTTP request to Core (web1/app.py).
The caller passes it via the `X-TRACE-ID` header.
web1/app.py reads it with `request.headers.get("X-TRACE-ID")`.
If the caller passes `"auto"`, web1 generates a UUID for convenience (browser use).
Pravah, Sarathi, and Executer never generate trace_ids on their own.

---

**Q2. Why does execution fail without Sarathi?**

Because executer/app.py has a hard check:
```python
if request.headers.get("X-CALLER") != "sarathi":
    return jsonify({"error": "unauthorized"}), 403
```
Any call to `/execute-action` without `X-CALLER: sarathi` returns HTTP 403 immediately.
This means nothing can trigger execution except Sarathi.

---

**Q3. How do I debug missing signals?**

Step 1: Check if the event reached Monitor:
```bash
curl -X POST http://54.156.236.10:30004/track-event \
  -H "Content-Type: application/json" \
  -d '{"user_id":"debug","event_type":"test","timestamp":1234,"session_id":"s1","trace_id":"test-trace"}'
```
Should return `{"status":"ok"}`. If not → Monitor pod is down.

Step 2: Check the stream is live:
```bash
curl -H "Host: pravah.blackholeinfiverse.com" -N http://54.156.236.10/signals/stream
```
Should show keepalives. If not → nginx or monitor pod issue.

Step 3: Check pod logs:
```bash
kubectl logs deployment/monitor -n default
kubectl logs deployment/sarathi -n default
kubectl logs deployment/executer -n prod
```

---

**Q4. What breaks if trace_hash mismatches?**

Nothing breaks automatically — trace_hash is computed by Monitor and attached to every signal.
It is SHA-256 of the trace_id string. It is there for external verification only.
If you take any signal from the stream and compute `SHA-256(signal.trace_id)`, it should equal `signal.trace_hash`.
If it doesn't match, the trace_id was mutated somewhere between Core and Monitor — which should never happen.

---

**Q5. What is the difference between execution and verification signals?**

`execution` — emitted BEFORE kubectl runs. `value: "RUNNING"`. Does NOT tell you if it worked.
`verification` — emitted AFTER kubectl returns. `value: "SUCCESS"` or `"FAILURE"`. Tells you what actually happened.
They share the same `execution_id` so you can link them together.

---

**Q6. Can I call Sarathi without a prior login event?**

Yes. Sarathi only requires a `trace_id` in the request body. It does not check whether that trace_id has a prior login event.
The login and the Sarathi decision are independent flows. They are linked only by sharing the same trace_id in the stream.

---

**Q7. What happens if Monitor goes down?**

Events from web1, Sarathi, and Executer will fail silently — they use `requests.post()` without error handling.
The execution itself (kubectl) still runs if Sarathi can reach Executer.
Signals will be lost — they are in-memory only (deque). No persistence.
When Monitor comes back up, new events will stream normally.

---

**Q8. How do I add a new service to the allowed list?**

In `executer/app.py`:
```python
ALLOWED_SERVICES = ["web1-blue", "web1-green", "web2-blue", "web2-green"]
```
Add the new service name here, rebuild and push the Docker image, then restart the executer pod:
```bash
kubectl rollout restart deployment/executer -n prod
```

---

**Q9. How do I add a new governance rule?**

In `executer/governance.py`:
```python
def validate_deployment_request(service_id, action):
    if not service_id:
        return "BLOCK"
    if action == "scale_up" and service_id == "critical-service":
        return "BLOCK"
    return "ALLOW"
```
Add a new `if` condition, return `"BLOCK"` to prevent execution or `"ALLOW"` to permit.

---

**Q10. Why do I see login_detected twice in the stream for one login?**

web1/app.py posts three events for each login: `session_start`, `user_login`, `page_view`.
Both `session_start` and `user_login` map to `login_detected` in Monitor's EVENT_TO_SIGNAL table:
```python
"session_start": ("login_detected", ...),
"user_login":    ("login_detected", ...),
```
This is expected. Two `login_detected` signals appear, then one `user_interaction` for `page_view`.

---

**Q11. How do I redeploy a service after changing code?**

1. Build and push the Docker image:
```bash
docker build -t rayyandevopss/<service>-service:latest ./<service>/
docker push rayyandevopss/<service>-service:latest
```
2. Restart the pod:
```bash
kubectl rollout restart deployment/monitor       # for monitor
kubectl rollout restart deployment/sarathi       # for sarathi
kubectl rollout restart deployment/executer -n prod  # for executer
```

---

**Q12. Why is executer in the `prod` namespace but monitor and sarathi are in `default`?**

Executer needs a ServiceAccount (`executer-sa`) with kubectl permissions to patch deployments in `prod`.
This is defined in `k8s/executer-rbac.yml`.
Monitor and Sarathi don't touch Kubernetes resources directly, so they don't need special permissions.

---

**Q13. How do I change the decision threshold?**

In `sarathi/app.py`:
```python
if score > 0.6:
    decision_status = "ALLOW"
elif score > 0.35:
    decision_status = "ESCALATE"
else:
    decision_status = "BLOCK"
```
Change `0.6` to your desired threshold. Rebuild and redeploy Sarathi.
Also update `policy_reference` string to match your new threshold for clarity.

---

**Q14. What does enforcement_status: "validated" mean exactly?**

It means Sarathi checked its own decision and confirmed it is safe to proceed to execution.
It is emitted after ALLOW, before calling Executer.
It is an observed fact — Sarathi posted this event, so the gate was passed.
It is not checked by anything else — it is purely for stream visibility.

---

**Q15. How do I verify the full system is working in one command?**

Run the demo script:
```bash
bash scripts/handover_demo.sh
```

Or manually:
```bash
# Terminal 1 — stream
curl -H "Host: pravah.blackholeinfiverse.com" -N http://54.156.236.10/signals/stream

# Terminal 2
TRACE=$(uuidgen)
curl -X POST http://54.156.236.10:30001/login -H "X-TRACE-ID: $TRACE" -d "user_id=test"
curl -X POST http://54.156.236.10:30005/decision \
  -H "Content-Type: application/json" \
  -d "{\"trace_id\":\"$TRACE\",\"service_id\":\"web1-blue\",\"action_type\":\"restart\",\"payload\":{\"decision_score\":0.9}}"
```

If Terminal 1 shows 8 signals all sharing the same trace_id — system is fully operational.