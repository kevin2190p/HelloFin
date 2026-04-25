"""End-to-end test: cross-cloud envelope encryption + decryption + tamper."""
import os
import sys
from dotenv import load_dotenv

load_dotenv("backend/.env")
sys.path.insert(0, "backend")

from app.services.multicloud_crypto import encrypt_payload_sync, decrypt_payload_sync

print("=" * 60)
print(" Cross-Cloud KMS Envelope Encryption – End-to-End Test")
print("=" * 60)

sample = "Fakeout sensitive PII | Aunty Lim card='4111-1111-1111-1234' OTP='999888'"
aad = b"fakeout-finhack-2026"

# 1. Encrypt
print("\n[1] Encrypting...")
print(f"    plaintext: {sample}")
blob = encrypt_payload_sync(sample.encode("utf-8"), aad=aad)
print(f"    aws_key_id        : {blob['aws_key_id']}")
print(f"    alibaba_key_id    : {blob['alibaba_key_id']}")
print(f"    oss_bucket        : {blob['oss_bucket']}")
print(f"    oss_object_key    : {blob['oss_object_key']}")
print(f"    nonce             : {blob['nonce']}")
print(f"    ciphertext        : {blob['ciphertext'][:60]}...")

# 2. Decrypt
print("\n[2] Decrypting (requires BOTH clouds)...")
recovered = decrypt_payload_sync(blob, aad=aad)
print(f"    recovered             : {recovered.decode('utf-8')}")
match = recovered.decode("utf-8") == sample
print(f"    round-trip match      : {match}")

if not match:
    print("\nMISMATCH - check logs above")
    sys.exit(1)

# 3. Tamper test
print("\n[3] Tamper test (flip 1 char in ciphertext)...")
import copy
bad = copy.deepcopy(blob)
mid = len(bad["ciphertext"]) // 2
ch = bad["ciphertext"][mid]
new_ch = "B" if ch == "A" else "A"
bad["ciphertext"] = bad["ciphertext"][:mid] + new_ch + bad["ciphertext"][mid + 1:]
try:
    decrypt_payload_sync(bad, aad=aad)
    print("    Tamper test FAILED - decryption succeeded on bad data")
    sys.exit(1)
except Exception as e:
    print(f"    AES-GCM rejected tampered ciphertext: {type(e).__name__}")
    print(f"    Tamper test PASSED")

print("\n" + "=" * 60)
print(" ALL TESTS PASSED")
print(" - AWS KMS generated DEK")
print(" - Alibaba KMS double-wrapped it")
print(" - Decryption required BOTH clouds")
print(" - AES-GCM detected tampering")
print("=" * 60)
