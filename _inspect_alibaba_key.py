"""Inspect the Alibaba KMS key to see what state/usage it supports."""
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")

from alibabacloud_kms20160120.client import Client as KmsClient
from alibabacloud_kms20160120 import models as kms_models
from alibabacloud_tea_openapi import models as open_api_models

ak    = os.getenv("ALIBABA_ACCESS_KEY_ID", "").strip()
sk    = os.getenv("ALIBABA_ACCESS_KEY_SECRET", "").strip()
tok   = os.getenv("ALIBABA_SECURITY_TOKEN", "").strip()
region = os.getenv("ALIBABA_KMS_REGION", "").strip()
key_id = os.getenv("ALIBABA_KMS_KEY_ID", "").strip()

cfg_kwargs = dict(
    access_key_id=ak,
    access_key_secret=sk,
    endpoint=f"kms.{region}.aliyuncs.com",
)
if tok:
    cfg_kwargs["security_token"] = tok
    cfg_kwargs["type"] = "sts"
client = KmsClient(open_api_models.Config(**cfg_kwargs))

# DescribeKey
print(f"DescribeKey({key_id}) in {region}...")
req = kms_models.DescribeKeyRequest(key_id=key_id)
resp = client.describe_key(req)
m = resp.body.key_metadata
print(f"  Full metadata as dict:")
import json as _j
print(_j.dumps(m.to_map(), indent=2, default=str))
print()

# GenerateDataKey via Alibaba (this is what we'll use eventually)
print(f"Trying Alibaba GenerateDataKey (without our envelope)...")
try:
    req2 = kms_models.GenerateDataKeyRequest(key_id=key_id, number_of_bytes=32)
    resp2 = client.generate_data_key(req2)
    print(f"  GenerateDataKey OK")
    print(f"  Plaintext (b64) : {resp2.body.plaintext[:30]}...")
    print(f"  CiphertextBlob  : {resp2.body.ciphertext_blob[:30]}...")
except Exception as e:
    print(f"  GenerateDataKey FAILED: {str(e)[:150]}")

print()
print(f"Trying Encrypt directly...")
try:
    import base64
    req3 = kms_models.EncryptRequest(key_id=key_id, plaintext=base64.b64encode(b"hello").decode())
    resp3 = client.encrypt(req3)
    print(f"  Encrypt OK, CiphertextBlob: {resp3.body.ciphertext_blob[:30]}...")
except Exception as e:
    print(f"  Encrypt FAILED: {str(e)[:200]}")
