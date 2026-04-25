"""
Cross-Cloud KMS Envelope Encryption – Fakeout Zero-Trust Vault
================================================================
Encryption flow (each call uses a *fresh* Data Encryption Key):

  AWS KMS GenerateDataKey ──▶ plaintext_DEK + aws_wrapped_DEK
                                                  │
                                                  ▼
                               Alibaba OSS PutObject (SSE-KMS)
                               with x-oss-server-side-encryption: KMS
                               and  x-oss-kms-key-id: <our Alibaba KMS CMK>
                                                  │
                                                  ▼
                            object stored at oss://bucket/<random key>
                            (encrypted at rest by Alibaba KMS internally)

  AES-256-GCM(plaintext_DEK, plaintext)  ──▶ ciphertext + nonce + tag
  (plaintext_DEK is then immediately discarded from memory.)

Decryption requires BOTH clouds:
   1. Alibaba creds + OSS GetObject  → returns aws_wrapped_DEK
        (OSS auto-decrypts at rest via Alibaba KMS CMK)
   2. AWS KMS Decrypt(aws_wrapped_DEK) → plaintext_DEK
   3. AES-256-GCM decrypt with plaintext_DEK → plaintext

Threat model – an attacker who steals data + only ONE cloud's creds
gets nothing useful:
   • Without Alibaba creds → can't even download the wrapped DEK
   • Without AWS creds → the wrapped DEK can't be unwrapped
   • Without both → permanently unrecoverable

NOTE on the architecture: We originally tried double-wrapping the DEK
directly with both KMS APIs, but Alibaba KMS 3.0 Default Keys block
direct Encrypt/Decrypt API calls (paid dedicated KMS instance required
for that). OSS-SSE-KMS gives us the same zero-trust guarantee using
Alibaba KMS as a service integration – Alibaba KMS still encrypts the
wrapped-DEK at rest, with OSS as the only authorised caller.
"""

import asyncio
import base64
import json
import os
from typing import Optional, Tuple

import structlog
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = structlog.get_logger("fakeout.multicloud_crypto")

SCHEME_VERSION = "multicloud-envelope-v1"
NONCE_BYTES = 12  # 96-bit nonce, recommended for AES-GCM


# ----------------------------------------------------------------------
# AWS KMS helpers
# ----------------------------------------------------------------------
def _aws_kms_client():
    import boto3  # already installed via requirements.txt
    ak = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    if not ak or ak.startswith("REPLACE"):
        raise RuntimeError("AWS_ACCESS_KEY_ID not configured")
    kwargs = {
        "aws_access_key_id": ak,
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "region_name": (
            os.getenv("AWS_KMS_REGION")
            or os.getenv("AWS_BEDROCK_REGION")
            or "ap-southeast-1"
        ),
    }
    tok = os.getenv("AWS_SESSION_TOKEN", "").strip()
    if tok and not tok.startswith("REPLACE"):
        kwargs["aws_session_token"] = tok
    return boto3.client("kms", **kwargs)


def _aws_generate_dek(aws_key_id: str) -> Tuple[bytes, bytes]:
    """Returns (plaintext_dek, aws_wrapped_dek_blob)."""
    kms = _aws_kms_client()
    resp = kms.generate_data_key(KeyId=aws_key_id, KeySpec="AES_256")
    return resp["Plaintext"], resp["CiphertextBlob"]


def _aws_decrypt_dek(aws_wrapped_dek: bytes) -> bytes:
    kms = _aws_kms_client()
    resp = kms.decrypt(CiphertextBlob=aws_wrapped_dek)
    return resp["Plaintext"]


# ----------------------------------------------------------------------
# Alibaba OSS (SSE-KMS) helpers – the second wrap layer
# ----------------------------------------------------------------------
def _alibaba_oss_bucket():
    """Build an oss2 Bucket client. Supports both permanent RAM AccessKeys
    (LTAI...) and STS temp credentials (STS....)."""
    import oss2
    ak = os.getenv("ALIBABA_ACCESS_KEY_ID", "").strip()
    sk = os.getenv("ALIBABA_ACCESS_KEY_SECRET", "").strip()
    if not ak or ak.startswith("REPLACE"):
        raise RuntimeError("ALIBABA_ACCESS_KEY_ID not configured")
    sts_token = os.getenv("ALIBABA_SECURITY_TOKEN", "").strip()
    bucket_name = os.getenv("ALIBABA_OSS_BUCKET", "").strip()
    if not bucket_name or bucket_name.startswith("REPLACE"):
        raise RuntimeError("ALIBABA_OSS_BUCKET not configured")
    endpoint = os.getenv(
        "ALIBABA_OSS_ENDPOINT",
        "https://oss-ap-southeast-3.aliyuncs.com",
    )
    if sts_token and not sts_token.startswith("REPLACE"):
        auth = oss2.StsAuth(ak, sk, sts_token)
    else:
        auth = oss2.Auth(ak, sk)
    return oss2.Bucket(auth, endpoint, bucket_name)


def _alibaba_wrap(aws_wrapped_dek: bytes, alibaba_key_id: str) -> str:
    """Stores the AWS-wrapped DEK in OSS as an SSE-KMS-encrypted object.
    Returns the OSS object key (which is what the caller persists)."""
    import uuid
    bucket = _alibaba_oss_bucket()
    object_key = f"fakeout-dek/{uuid.uuid4()}.bin"
    headers = {
        "x-oss-server-side-encryption": "KMS",
        "x-oss-server-side-encryption-key-id": alibaba_key_id,
    }
    bucket.put_object(object_key, aws_wrapped_dek, headers=headers)
    logger.info(
        "alibaba_oss_sse_kms_put_ok",
        object_key=object_key,
        bytes=len(aws_wrapped_dek),
        kms_key_id=alibaba_key_id,
    )
    return object_key


def _alibaba_unwrap(oss_object_key: str) -> bytes:
    """Retrieves the AWS-wrapped DEK from OSS. OSS auto-decrypts via the
    Alibaba KMS CMK that was used at upload time."""
    bucket = _alibaba_oss_bucket()
    obj = bucket.get_object(oss_object_key)
    data = obj.read()
    logger.info(
        "alibaba_oss_sse_kms_get_ok",
        object_key=oss_object_key,
        bytes=len(data),
    )
    return data


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
def encrypt_payload_sync(plaintext: bytes, aad: Optional[bytes] = None) -> dict:
    """
    Encrypt `plaintext` with a fresh DEK. The DEK is generated by AWS KMS
    and stored in Alibaba OSS encrypted-at-rest with the Alibaba KMS CMK.
    `aad` (additional authenticated data) is bound into the AES-GCM tag.
    """
    aws_key_id = os.getenv("AWS_KMS_KEY_ID", "").strip()
    alibaba_key_id = os.getenv("ALIBABA_KMS_KEY_ID", "").strip()
    if not aws_key_id or aws_key_id.startswith("REPLACE"):
        raise RuntimeError("AWS_KMS_KEY_ID not configured")
    if not alibaba_key_id or alibaba_key_id.startswith("REPLACE"):
        raise RuntimeError("ALIBABA_KMS_KEY_ID not configured")

    # --- 1. AWS generates a fresh DEK ---
    plaintext_dek, aws_wrapped_dek = _aws_generate_dek(aws_key_id)
    logger.info("aws_kms_generate_data_key_ok",
                key_id=aws_key_id,
                dek_bytes=len(plaintext_dek),
                wrapped_bytes=len(aws_wrapped_dek))

    # --- 2. Stash AWS-wrapped DEK in Alibaba OSS w/ SSE-KMS ---
    oss_object_key = _alibaba_wrap(aws_wrapped_dek, alibaba_key_id)
    logger.info("alibaba_kms_wrap_ok",
                key_id=alibaba_key_id,
                oss_object_key=oss_object_key)

    # --- 3. AES-256-GCM encrypt the actual data ---
    aesgcm = AESGCM(plaintext_dek)
    nonce = os.urandom(NONCE_BYTES)
    ct = aesgcm.encrypt(nonce, plaintext, aad)

    # --- 4. Wipe the plaintext DEK from memory ---
    # (Python can't truly wipe bytes, but we drop our last reference.)
    del plaintext_dek

    blob = {
        "scheme": SCHEME_VERSION,
        "oss_object_key": oss_object_key,
        "oss_bucket": os.getenv("ALIBABA_OSS_BUCKET"),
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ct).decode(),
        "aws_key_id": aws_key_id,
        "alibaba_key_id": alibaba_key_id,
    }
    logger.info("multicloud_envelope_encrypt_ok",
                scheme=SCHEME_VERSION,
                ciphertext_bytes=len(ct))
    return blob


def decrypt_payload_sync(blob: dict, aad: Optional[bytes] = None) -> bytes:
    """
    Decrypt a blob produced by `encrypt_payload`.
    Requires BOTH AWS KMS and Alibaba OSS+KMS to be reachable + authorised.
    """
    if blob.get("scheme") != SCHEME_VERSION:
        raise ValueError(f"unsupported envelope scheme: {blob.get('scheme')}")

    # --- 1. Pull AWS-wrapped DEK from Alibaba OSS (auto-decrypts via Alibaba KMS) ---
    aws_wrapped_dek = _alibaba_unwrap(blob["oss_object_key"])
    logger.info("alibaba_kms_unwrap_ok", inner_bytes=len(aws_wrapped_dek))

    # --- 2. AWS unwraps the inner layer (recovers plaintext DEK) ---
    plaintext_dek = _aws_decrypt_dek(aws_wrapped_dek)
    logger.info("aws_kms_decrypt_ok", dek_bytes=len(plaintext_dek))

    # --- 3. AES-GCM decrypt + verify tag ---
    aesgcm = AESGCM(plaintext_dek)
    nonce = base64.b64decode(blob["nonce"])
    ct = base64.b64decode(blob["ciphertext"])
    plaintext = aesgcm.decrypt(nonce, ct, aad)

    del plaintext_dek
    logger.info("multicloud_envelope_decrypt_ok", plaintext_bytes=len(plaintext))
    return plaintext


# Async wrappers so FastAPI handlers don't block the event loop on KMS calls
async def encrypt_payload(plaintext: bytes, aad: Optional[bytes] = None) -> dict:
    return await asyncio.to_thread(encrypt_payload_sync, plaintext, aad)


async def decrypt_payload(blob: dict, aad: Optional[bytes] = None) -> bytes:
    return await asyncio.to_thread(decrypt_payload_sync, blob, aad)
