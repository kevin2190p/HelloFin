"""Test if we can use Alibaba OSS with the current credentials."""
import os
import sys
from dotenv import load_dotenv
load_dotenv("backend/.env")

import oss2
from oss2.credentials import StaticCredentialsProvider

ak    = os.getenv("ALIBABA_ACCESS_KEY_ID", "").strip()
sk    = os.getenv("ALIBABA_ACCESS_KEY_SECRET", "").strip()
tok   = os.getenv("ALIBABA_SECURITY_TOKEN", "").strip()
region = "ap-southeast-3"  # Match the KMS key region (KL)

bucket_name = "hellofin-finhack-vault"  # globally unique-ish
endpoint = f"https://oss-{region}.aliyuncs.com"

print(f"Region    : {region}")
print(f"Endpoint  : {endpoint}")
print(f"Bucket    : {bucket_name}")
print()

# Build auth with STS support
if tok:
    auth = oss2.StsAuth(ak, sk, tok)
else:
    auth = oss2.Auth(ak, sk)

# 1. Try ListBuckets (lightweight check)
service = oss2.Service(auth, endpoint)
try:
    print("ListBuckets:")
    for i, b in enumerate(oss2.BucketIterator(service)):
        print(f"  - {b.name} ({b.location})")
        if i >= 10:
            print("  ... (truncated)")
            break
    else:
        if i == 0:
            print("  (no buckets yet)")
except Exception as e:
    print(f"  FAILED: {e}")
    sys.exit(1)

# 2. Try to create the bucket
print()
print(f"Creating bucket {bucket_name}...")
bucket = oss2.Bucket(auth, endpoint, bucket_name)
try:
    bucket.create_bucket(oss2.BUCKET_ACL_PRIVATE)
    print(f"  OK")
except oss2.exceptions.OssError as e:
    if "BucketAlreadyExists" in str(e) or "TooManyBuckets" in str(e):
        print(f"  Already exists or limit reached: {e.code}")
    else:
        print(f"  FAILED: {e}")
        sys.exit(1)

# 3. Try a small upload
print()
print("Uploading test object...")
try:
    bucket.put_object("test-canary.txt", b"hello cross-cloud")
    print("  OK")
    obj = bucket.get_object("test-canary.txt")
    print(f"  Read back: {obj.read()!r}")
except Exception as e:
    print(f"  FAILED: {e}")
    sys.exit(1)

print()
print("OSS works. Ready to use as KMS-encrypted key vault.")
