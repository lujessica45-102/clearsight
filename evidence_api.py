"""Closure Call backend on Akamai (Linode).

- Serves the React frontend (built files in ./web)
- /api/current : live data for the frontend (teammates' agent POSTs it, the UI GETs it)
- /evidence    : tamper-evident decision records in Akamai Object Storage
- /vault       : simple evidence viewer page
"""
import os, json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import evidence  # also loads .env

app = FastAPI(title="Closure Call - Akamai backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
TOKEN = os.environ.get("EVIDENCE_TOKEN", "")
HERE = Path(__file__).parent
WEB = HERE / "web"
CURRENT_KEY = "current/latest.json"


def check_token(tok: str):
    if not TOKEN or tok != TOKEN:
        raise HTTPException(401, "Missing or wrong X-Evidence-Token")


class SaveRequest(BaseModel):
    facility_id: str
    record: dict


@app.get("/health")
def health():
    return {"ok": True}


# ---------- Evidence (Akamai Object Storage) ----------
@app.post("/evidence")
def save(body: SaveRequest, x_evidence_token: str = Header(default="")):
    check_token(x_evidence_token)
    return {"evidence_id": evidence.save_evidence(body.facility_id, body.record)}


@app.get("/evidence")
def list_records(facility_id: str):
    return {"facility_id": facility_id, "evidence_ids": evidence.list_evidence(facility_id)}


@app.get("/evidence/{evidence_id:path}")
def get_record(evidence_id: str):
    try:
        return evidence.get_evidence(evidence_id)
    except Exception:
        raise HTTPException(404, "Evidence not found")


# ---------- Live data for the frontend ----------
@app.get("/api/current")
def get_current():
    try:
        obj = evidence._s3.get_object(Bucket=evidence._BUCKET, Key=CURRENT_KEY)
        return json.loads(obj["Body"].read())
    except Exception:
        raise HTTPException(404, "No live data yet")


@app.post("/api/current")
async def set_current(request: Request, x_evidence_token: str = Header(default="")):
    """The agent posts the full snapshot (same shape as MOCK in frontend/src/data.js).
    It becomes what the UI shows, and each facility's decision is saved as evidence."""
    check_token(x_evidence_token)
    body = await request.json()
    evidence._s3.put_object(Bucket=evidence._BUCKET, Key=CURRENT_KEY,
                            Body=json.dumps(body).encode(), ContentType="application/json")
    ids = [evidence.save_evidence(f.get("id", "unknown"), {"alert": body.get("alert"), "facility": f})
           for f in body.get("facilities", [])]
    return {"ok": True, "evidence_ids": ids}


# ---------- Pages ----------
@app.get("/vault", response_class=HTMLResponse)
def vault():
    return (HERE / "viewer.html").read_text()


@app.get("/{path:path}")
def frontend(path: str):
    """Serve the built React app; unknown paths fall back to index.html (client-side routing)."""
    target = (WEB / path).resolve()
    if path and target.is_file() and WEB.resolve() in target.parents:
        return FileResponse(target)
    index = WEB / "index.html"
    if index.exists():
        return FileResponse(index)
    return HTMLResponse((HERE / "viewer.html").read_text())
