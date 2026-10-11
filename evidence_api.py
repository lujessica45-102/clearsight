import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import evidence  # also loads .env

app = FastAPI(title="Closure Call - Evidence")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
TOKEN = os.environ.get("EVIDENCE_TOKEN", "")

class SaveRequest(BaseModel):
    facility_id: str
    record: dict

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/evidence")
def save(body: SaveRequest, x_evidence_token: str = Header(default="")):
    if not TOKEN or x_evidence_token != TOKEN:
        raise HTTPException(401, "Missing or wrong X-Evidence-Token")
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

@app.get("/", response_class=HTMLResponse)
def viewer():
    return (Path(__file__).parent / "viewer.html").read_text()
