"""Quick smoke test: can we reach AWS KMS with the loaded creds?"""
import os
import sys
from dotenv import load_dotenv

load_dotenv("backend/.env")

import boto3
from botocore.exceptions import ClientError

try:
    kms = boto3.client(
        "kms",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        region_name=os.getenv("AWS_KMS_REGION", "ap-southeast-1"),
    )
    key_id = os.getenv("AWS_KMS_KEY_ID")
    print(f"Calling KMS GenerateDataKey on {key_id}...")
    resp = kms.generate_data_key(KeyId=key_id, KeySpec="AES_256")
    print(f"  AWS KMS OK")
    print(f"  Plaintext DEK : {len(resp['Plaintext'])} bytes")
    print(f"  Wrapped DEK   : {len(resp['CiphertextBlob'])} bytes (encrypted by KMS)")
    print()
    print("AWS leg works. Ready for Alibaba.")
except ClientError as e:
    print(f"AWS error: {e.response['Error']['Code']} - {e.response['Error']['Message']}")
    sys.exit(1)
except Exception as e:
    print(f"Failed: {type(e).__name__}: {e}")
    sys.exit(1)
