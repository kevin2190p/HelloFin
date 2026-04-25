"""Smoke test: can we use Alibaba STS creds to talk to KMS?"""
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv("backend/.env")
sys.path.insert(0, "backend")

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.auth.credentials import StsTokenCredential

ak    = os.getenv("ALIBABA_ACCESS_KEY_ID", "").strip()
sk    = os.getenv("ALIBABA_ACCESS_KEY_SECRET", "").strip()
tok   = os.getenv("ALIBABA_SECURITY_TOKEN", "").strip()
region = os.getenv("ALIBABA_KMS_REGION", "ap-southeast-1")

print(f"Using AccessKey ID: {ak}")
print(f"Has security token: {bool(tok)} (len={len(tok)})")
print(f"Region            : {region}")
print()

if tok and not tok.startswith("REPLACE"):
    cred = StsTokenCredential(ak, sk, tok)
    client = AcsClient(region_id=region, credential=cred)
else:
    client = AcsClient(ak, sk, region)

# Use ListKeys (lightest KMS call) to confirm we can hit the KMS API at all.
from aliyunsdkkms.request.v20160120.ListKeysRequest import ListKeysRequest
req = ListKeysRequest()
req.set_accept_format("json")

try:
    resp = json.loads(client.do_action_with_exception(req))
    keys = resp.get("Keys", {}).get("Key", [])
    print(f"Alibaba KMS ListKeys OK")
    print(f"  Total keys in this region: {resp.get('TotalCount', len(keys))}")
    for k in keys[:5]:
        print(f"    - {k.get('KeyId')}")
    if not keys:
        print("    (no KMS keys yet - you need to create one)")
    print()
    print("Alibaba creds work.")
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")
    sys.exit(1)
