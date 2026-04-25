"""Verify approve/cancel updates caregiver:alerts list (the dashboard polling source)."""
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8080"


def http(path, method="GET", payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=body,
        headers={"Content-Type": "application/json"} if body else {},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def show_pending():
    alerts = http("/caregiver/alerts")
    pending = [a for a in alerts if a.get("status") in ("held", "pending")]
    return alerts, pending


# 1. Create two HIGH-risk alerts via the scan endpoint
print("=== Step 1: create two HIGH-risk alerts ===")
r1 = http("/risk/scan", "POST", {"message": "This is PDRM. Your account is under investigation. Transfer to safe account now or arrest warrant issued."})
r2 = http("/risk/scan", "POST", {"message": "Hi mum, I'm in trouble. Phone rosak, please transfer RM5000 now to this new account, don't tell dad, urgent emergency!"})
print(f"  scan #1 -> score={r1['riskScore']}, status={r1['status']}")
print(f"  scan #2 -> score={r2['riskScore']}, status={r2['status']}")

# 2. Inspect the dashboard list and pull two txn_ids that are still 'held'
all_alerts, pending = show_pending()
print(f"\n=== Step 2: dashboard list has {len(all_alerts)} alerts, {len(pending)} pending ===")
for a in pending[:5]:
    print(f"  - {a['txn_id'][:8]}... status={a['status']} score={a['risk_score']}")

if len(pending) < 2:
    print("Not enough pending alerts to test approve+cancel"); sys.exit(1)

approve_id = pending[0]["txn_id"]
cancel_id  = pending[1]["txn_id"]
pending_before = len(pending)

# 3. Approve one, cancel the other
print(f"\n=== Step 3: APPROVE {approve_id[:8]}... and CANCEL {cancel_id[:8]}... ===")
ar = http(f"/caregiver/approve/{approve_id}", "POST")
cr = http(f"/caregiver/cancel/{cancel_id}", "POST")
print(f"  approve  -> {ar.get('action')}: {ar.get('message')}")
print(f"  cancel   -> {cr.get('action')}: {cr.get('message')}")

# 4. Re-fetch the polling endpoint and verify the list is updated
all_after, pending_after = show_pending()
print(f"\n=== Step 4: dashboard list AFTER actions ({len(pending_after)} pending) ===")
target = {a["txn_id"]: a["status"] for a in all_after if a["txn_id"] in (approve_id, cancel_id)}
print(f"  approved alert status in list: {target.get(approve_id)}")
print(f"  cancelled alert status in list: {target.get(cancel_id)}")
print(f"  pending count: {pending_before} -> {len(pending_after)} (delta: {len(pending_after) - pending_before})")

ok_a = target.get(approve_id) == "approved"
ok_c = target.get(cancel_id) == "cancelled"
ok_dec = len(pending_after) <= pending_before - 2
print()
print(f"  [{'PASS' if ok_a else 'FAIL'}] approved status synced to caregiver:alerts list")
print(f"  [{'PASS' if ok_c else 'FAIL'}] cancelled status synced to caregiver:alerts list")
print(f"  [{'PASS' if ok_dec else 'FAIL'}] pending count decremented by at least 2")

sys.exit(0 if (ok_a and ok_c and ok_dec) else 1)
