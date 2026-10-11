"""Closure Call backend on Akamai (Linode).

- Serves the React frontend (built files in ./web)
- /api/current : live data for the frontend (teammates' agent POSTs it, the UI GETs it)
- /evidence    : tamper-evident decision records in Akamai Object Storage
- /vault       : simple evidence viewer page
"""
import os, json, hashlib, threading, time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
try:  # needs the OBJ_* object-storage settings; without them the app still serves weather/decision data
    import evidence  # also loads .env
    EVIDENCE_ERROR = None
except Exception as e:
    evidence = None
    EVIDENCE_ERROR = f"{type(e).__name__}: {e}"
    print("Evidence storage not configured (evidence routes disabled):", EVIDENCE_ERROR)

try:  # connector to the teammates' backend (backend/connect.py -> parser/) and the as-of clock
    from backend.connect import build_snapshot
    from closure.clock import resolve_as_of, ClockError
except Exception as e:
    build_snapshot = None
    resolve_as_of = None
    ClockError = ValueError
    print("Teammates' backend not available:", e)

app = FastAPI(title="Closure Call - Akamai backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
TOKEN = os.environ.get("EVIDENCE_TOKEN", "")
HERE = Path(__file__).parent
WEB = HERE / "web"
CURRENT_KEY = "current/latest.json"


def need_evidence():
    if evidence is None:
        raise HTTPException(503, "Evidence storage is not configured on this server (OBJ_* settings missing). " + (EVIDENCE_ERROR or ""))


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
    need_evidence()
    check_token(x_evidence_token)
    return {"evidence_id": evidence.save_evidence(body.facility_id, body.record)}


@app.get("/evidence")
def list_records(facility_id: str):
    need_evidence()
    return {"facility_id": facility_id, "evidence_ids": evidence.list_evidence(facility_id)}


@app.get("/evidence/{evidence_id:path}")
def get_record(evidence_id: str):
    need_evidence()
    try:
        return evidence.get_evidence(evidence_id)
    except Exception:
        raise HTTPException(404, "Evidence not found")


# ---------- Live data for the frontend ----------
REFRESH_SECONDS = int(os.environ.get("REFRESH_SECONDS", "600"))
_cache = {"t": 0.0, "data": None, "busy": False}


def _alert_fingerprint(f):
    return hashlib.sha256(json.dumps(sorted(a.get("id") or "" for a in f.get("alerts", []))).encode()).hexdigest()


def _refresh():
    """Run the teammates' weather pipeline; save each office's NWS report as evidence when its alerts change."""
    if build_snapshot is None or _cache["busy"]:
        return []
    _cache["busy"] = True
    try:
        prev = {f["id"]: _alert_fingerprint(f) for f in (_cache["data"] or {}).get("facilities", [])}
        snap = build_snapshot()
        _cache.update(t=time.time(), data=snap)
        ids = []
        if evidence is None:
            return ids
        evidence._s3.put_object(Bucket=evidence._BUCKET, Key=CURRENT_KEY,
                                Body=json.dumps(snap, default=str).encode(), ContentType="application/json")
        for f in snap["facilities"]:
            if prev.get(f["id"]) != _alert_fingerprint(f):
                ids.append(evidence.save_evidence(f["id"], {
                    "captured_at": f.get("weatherCapturedAt"), "alerts": f.get("alerts", []),
                    "data_sources": f.get("dataSources", []), "status": f.get("status")}))
        return ids
    finally:
        _cache["busy"] = False


def _refresh_quietly():
    try:
        _refresh()
    except Exception as e:
        print("Refresh failed:", e)


_asof_cache, _asof_locks, _asof_guard = {}, {}, threading.Lock()
ASOF_TTL_SECONDS = int(os.environ.get("ASOF_CACHE_SECONDS", "300"))
ASOF_MAX_ENTRIES = 8


def _moment(asof):
    """Resolve the requested moment (query param > CLEARSIGHT_NOW > system clock); 400 if unusable."""
    if resolve_as_of is None:
        raise HTTPException(503, "The as-of backend is not available on this server.")
    try:
        return resolve_as_of(asof)
    except ClockError as e:
        raise HTTPException(400, str(e))


def _asof_snapshot(as_dt, requested):
    """Snapshot for a fixed moment, cached per minute and single-flight (concurrent reloads share one computation)."""
    key = as_dt.strftime("%Y-%m-%dT%H:%M")
    with _asof_guard:
        lock = _asof_locks.setdefault(key, threading.Lock())
    with lock:
        hit = _asof_cache.get(key)
        if hit and time.time() - hit[0] < ASOF_TTL_SECONDS:
            return hit[1]
        snap = build_snapshot(requested)   # the original request string (None = CLEARSIGHT_NOW), so clock.requested echoes it
        with _asof_guard:
            _asof_cache[key] = (time.time(), snap)
            while len(_asof_cache) > ASOF_MAX_ENTRIES:
                _asof_cache.pop(min(_asof_cache, key=lambda k: _asof_cache[k][0]))
        return snap


@app.get("/api/current")
def get_current(asof: str | None = None):
    """asof=<ISO-8601 UTC> returns the data for that moment (live NWS if it is now, NWS alert history if within about a
    week, IEM archive of NWS products if older). No asof = live, unless the server sets CLEARSIGHT_NOW."""
    as_dt, info = _moment(asof)
    if asof or info["source"] == "env":      # a specific moment: compute on demand
        if build_snapshot is None:
            raise HTTPException(503, "The as-of backend is not available on this server.")
        return _asof_snapshot(as_dt, asof)
    if _cache["data"] is None and evidence is not None:
        try:  # last saved snapshot (survives restarts)
            obj = evidence._s3.get_object(Bucket=evidence._BUCKET, Key=CURRENT_KEY)
            _cache["data"] = json.loads(obj["Body"].read())
        except Exception:
            pass
    if _cache["data"] is None:
        _refresh_quietly()  # first load: build it now
    if build_snapshot and not _cache["busy"] and time.time() - _cache["t"] > REFRESH_SECONDS:
        threading.Thread(target=_refresh_quietly, daemon=True).start()
    if _cache["data"] is None:
        raise HTTPException(404, "No live data yet")
    return _cache["data"]


@app.get("/api/clock")
def get_clock(asof: str | None = None):
    """How the app interprets a requested moment (mode: live / recent / archive) or why it cannot."""
    _, info = _moment(asof)
    return info


@app.get("/api/moments")
def get_moments():
    """Demo bookmarks: a place and a timestamp only. The weather for each is queried when selected."""
    p = HERE / "presets" / "moments.json"
    if not p.exists():
        return {"moments": []}
    try:
        d = json.loads(p.read_text())
    except Exception as e:
        raise HTTPException(500, f"presets/moments.json is not valid JSON: {e}")
    return {"moments": d["moments"] if isinstance(d, dict) else d}


@app.post("/api/refresh")
def force_refresh(x_evidence_token: str = Header(default="")):
    """Re-run the weather check now (handy right before the demo)."""
    check_token(x_evidence_token)
    ids = _refresh()
    snap = _cache["data"] or {}
    return {"ok": True, "generated_at": snap.get("generated_at"), "new_evidence": ids,
            "facilities": [{"name": f["name"], "alerts": len(f.get("alerts", []))} for f in snap.get("facilities", [])]}


@app.post("/api/current")
async def set_current(request: Request, x_evidence_token: str = Header(default="")):
    """The agent posts the full snapshot (same shape as MOCK in frontend/src/data.js).
    It becomes what the UI shows, and each facility's decision is saved as evidence."""
    need_evidence()
    check_token(x_evidence_token)
    body = await request.json()
    evidence._s3.put_object(Bucket=evidence._BUCKET, Key=CURRENT_KEY,
                            Body=json.dumps(body).encode(), ContentType="application/json")
    ids = [evidence.save_evidence(f.get("id", "unknown"), {"alert": body.get("alert"), "facility": f})
           for f in body.get("facilities", [])]
    return {"ok": True, "evidence_ids": ids}


# ---------- Decision history (Akamai Object Storage, written by backend/history.py --upload) ----------
_history = {"data": None, "at": 0}


@app.get("/api/history")
def history():
    if not _history["data"] or time.time() - _history["at"] > 300:
        try:
            obj = evidence._s3.get_object(Bucket=evidence._BUCKET, Key="history/index.json")
            _history.update(data=json.loads(obj["Body"].read()), at=time.time())
        except Exception as e:
            raise HTTPException(503, f"History not in the bucket yet: {type(e).__name__}")
    return {**_history["data"], "served_from": "Akamai Object Storage via Linode"}


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
