"""Save and retrieve decision evidence in Akamai Object Storage."""
import os, json, hashlib, uuid
from datetime import datetime, timezone
import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

_s3 = boto3.client(
    "s3",
    config=Config(request_checksum_calculation="when_required", response_checksum_validation="when_required"),
    endpoint_url=os.environ["OBJ_ENDPOINT"],
    aws_access_key_id=os.environ["OBJ_ACCESS_KEY"],
    aws_secret_access_key=os.environ["OBJ_SECRET_KEY"],
)
_BUCKET = os.environ["OBJ_BUCKET"]

def _hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

def save_evidence(facility_id: str, record: dict) -> str:
    now = datetime.now(timezone.utc)
    evidence_id = f"{facility_id}/{now:%Y-%m-%d}/{now:%H%M%S}-{uuid.uuid4().hex[:6]}"
    body = {"evidence_id": evidence_id, "facility_id": facility_id,
            "saved_at": now.isoformat(), "record": record}
    body["sha256"] = _hash(body["record"])
    _s3.put_object(Bucket=_BUCKET, Key=f"evidence/{evidence_id}.json",
                   Body=json.dumps(body, indent=2, default=str).encode(),
                   ContentType="application/json")
    return evidence_id

def get_evidence(evidence_id: str) -> dict:
    obj = _s3.get_object(Bucket=_BUCKET, Key=f"evidence/{evidence_id}.json")
    body = json.loads(obj["Body"].read())
    body["integrity_ok"] = (_hash(body["record"]) == body["sha256"])
    return body

def list_evidence(facility_id: str, limit: int = 50) -> list:
    resp = _s3.list_objects_v2(Bucket=_BUCKET, Prefix=f"evidence/{facility_id}/")
    keys = sorted((o["Key"] for o in resp.get("Contents", [])), reverse=True)[:limit]
    return [k[len("evidence/"):-len(".json")] for k in keys]
