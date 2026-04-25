"""Verify the new /risk/scan + /caregiver/alerts pipeline returns risk_reasons."""
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8080"

CASES = [
    ("HIGH English scam", "This is PDRM. Your account is under investigation for money laundering. Transfer to safe account now or arrest warrant will be issued. Do not hang up."),
    ("MEDIUM family request", "Hi, this is your nephew. My phone is rosak, can you transfer RM2000 to this new account? Emergency, please don't tell mum."),
    ("SAFE message", "Hi mum, just confirming dinner at 7pm tonight at the usual restaurant. See you soon!"),
]


def post(path, payload):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get(path):
    with urllib.request.urlopen(f"{BASE}{path}", timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


for label, msg in CASES:
    print(f"=== {label} ===")
    r = post("/risk/scan", {"message": msg})
    print(f"  score={r.get('riskScore')}  status={r.get('status')}")
    print(f"  reasons (categorical): {r.get('reasons')}")
    print()

print("=== Dashboard alerts (newest first) ===")
alerts = get("/caregiver/alerts")
for a in alerts[:3]:
    print(f"--- score={a.get('risk_score')}  status={a.get('status')} ---")
    print(f"  transcript: {a.get('transcript')[:80]}")
    reasons = a.get("risk_reasons") or []
    if reasons:
        print(f"  risk_reasons ({len(reasons)}):")
        for i, rs in enumerate(reasons, 1):
            print(f"    {i}. {rs}")
    else:
        print("  risk_reasons: (none)")
    print()

sys.exit(0)
