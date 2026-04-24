"""
Multi-Cloud Clients – AWS + Alibaba Cloud
"""
import os, json
import structlog

logger = structlog.get_logger("hellofin.cloud")


def invoke_aws_lambda(payload: dict) -> dict:
    """Invoke AWS Lambda for secondary risk scoring."""
    ak = os.getenv("AWS_ACCESS_KEY_ID")
    if not ak or ak.startswith("REPLACE"):
        return {"risk_score": None, "status": "skipped"}
    try:
        import boto3
        client = boto3.client("lambda",
            aws_access_key_id=ak,
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "ap-southeast-1"))
        resp = client.invoke(FunctionName=os.getenv("AWS_LAMBDA_FUNCTION_NAME", "hellofin-risk-scorer"),
            InvocationType="RequestResponse", Payload=json.dumps(payload))
        return json.loads(resp["Payload"].read().decode())
    except Exception as e:
        logger.error("aws_lambda_error", error=str(e))
        return {"risk_score": None, "error": str(e)}


def upload_to_alibaba_oss(file_path: str, bucket: str, key: str) -> dict:
    """Upload audio to Alibaba OSS with AES256 server-side encryption."""
    ak = os.getenv("ALIBABA_ACCESS_KEY_ID")
    if not ak or ak.startswith("REPLACE"):
        return {"status": "skipped"}
    try:
        import oss2
        auth = oss2.Auth(ak, os.getenv("ALIBABA_ACCESS_KEY_SECRET"))
        b = oss2.Bucket(auth, os.getenv("ALIBABA_OSS_ENDPOINT"), bucket)
        result = b.put_object_from_file(key, file_path,
            headers={"x-oss-server-side-encryption": "AES256"})
        return {"status": "uploaded", "etag": result.etag}
    except Exception as e:
        logger.error("oss_error", error=str(e))
        return {"status": "error", "error": str(e)}


def encrypt_with_alibaba_kms(plaintext: str) -> dict:
    """Encrypt data via Alibaba KMS (placeholder)."""
    ak = os.getenv("ALIBABA_ACCESS_KEY_ID")
    if not ak or ak.startswith("REPLACE"):
        return {"status": "skipped"}
    try:
        from aliyunsdkcore.client import AcsClient
        from aliyunsdkkms.request.v20160120.EncryptRequest import EncryptRequest
        client = AcsClient(ak, os.getenv("ALIBABA_ACCESS_KEY_SECRET"),
            os.getenv("ALIBABA_KMS_REGION", "ap-southeast-1"))
        req = EncryptRequest()
        req.set_accept_format("json")
        req.set_KeyId(os.getenv("ALIBABA_KMS_KEY_ID"))
        req.set_Plaintext(plaintext)
        resp = json.loads(client.do_action_with_exception(req))
        return {"status": "encrypted", "ciphertext": resp.get("CiphertextBlob")}
    except Exception as e:
        logger.error("kms_error", error=str(e))
        return {"status": "error", "error": str(e)}
