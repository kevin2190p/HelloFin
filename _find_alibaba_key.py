"""Search multiple regions for the Alibaba KMS key."""
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")

from alibabacloud_kms20160120.client import Client as KmsClient
from alibabacloud_kms20160120 import models as kms_models
from alibabacloud_tea_openapi import models as open_api_models

ak    = os.getenv("ALIBABA_ACCESS_KEY_ID", "").strip()
sk    = os.getenv("ALIBABA_ACCESS_KEY_SECRET", "").strip()
tok   = os.getenv("ALIBABA_SECURITY_TOKEN", "").strip()
target = os.getenv("ALIBABA_KMS_KEY_ID", "").strip()

print(f"Looking for KMS key: {target}")
print()

regions = [
    "ap-southeast-1",  # Singapore
    "ap-southeast-3",  # Kuala Lumpur (Malaysia)
    "ap-southeast-5",  # Jakarta
    "ap-southeast-6",  # Manila
    "ap-southeast-7",  # Bangkok
    "cn-hongkong",     # Hong Kong
]

for region in regions:
    cfg_kwargs = dict(
        access_key_id=ak,
        access_key_secret=sk,
        endpoint=f"kms.{region}.aliyuncs.com",
    )
    if tok:
        cfg_kwargs["security_token"] = tok
        cfg_kwargs["type"] = "sts"
    try:
        client = KmsClient(open_api_models.Config(**cfg_kwargs))
        req = kms_models.ListKeysRequest()
        resp = client.list_keys(req)
        keys = resp.body.keys.key if resp.body.keys and resp.body.keys.key else []
        if keys:
            print(f"[{region}] {len(keys)} keys:")
            for k in keys:
                marker = " <-- MATCH" if target in (k.key_id, k.key_arn or "") else ""
                print(f"    {k.key_id}{marker}")
        else:
            print(f"[{region}] (empty)")
    except Exception as e:
        msg = str(e).split("Response:")[0][:100]
        print(f"[{region}] error: {msg}")
