"""ClearSight API + dashboard host.   Run from the repo root:  uvicorn closure.api:app --port 8000"""
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from parser import http_cache, nws_client

from . import clock, config, synthetic, workflow, store, agents
from .sectors import SECTORS, POSTURE_LABELS

app = FastAPI(title="ClearSight decision support")
_pool = ThreadPoolExecutor(4)
_jobs, _jobs_lock = {}, threading.Lock()


class EvaluateReq(BaseModel):
    facility_id: str
    as_of: str | None = None           # ISO-8601 moment to evaluate; omit for the app clock (CLEARSIGHT_NOW or real time)


class EvalRef(BaseModel):
    evaluation_id: str


class DecisionReq(BaseModel):
    evaluation_id: str
    selected_posture: str
    reason: str | None = None
    decided_by: str | None = None


def _submit(kind, evaluation_id, fn):
    jid = uuid.uuid4().hex[:10]
    with _jobs_lock:
        _jobs[jid] = {"job_id": jid, "kind": kind, "evaluation_id": evaluation_id, "status": "running", "result": None, "error": None}

    def run():
        try:
            res = fn()
            with _jobs_lock:
                _jobs[jid].update(status="done" if res.get("status") == "ok" else "failed", result=res, error=res.get("error"))
        except Exception as e:
            traceback.print_exc()
            with _jobs_lock:
                _jobs[jid].update(status="failed", error=f"{type(e).__name__}: {e}")
    _pool.submit(run)
    return {"job_id": jid, "status": "running"}


@app.get("/api/health")
def health():
    return {"ok": True, "model_id": config.BEDROCK_MODEL_ID, "fast_model_id": config.BEDROCK_FAST_MODEL_ID, "region": config.BEDROCK_REGION,
            "road_data": {"NE": bool(config.NE511_API_KEY), "FL": bool(config.FL511_API_KEY)}}


@app.get("/api/facilities")
def facilities():
    return {"synthetic_notice": synthetic.DISCLAIMER,
            "sectors": {k: {"label": v["label"], "description": v["description"], "params": v["params"], "rationale": v["rationale"]} for k, v in SECTORS.items()},
            "postures": POSTURE_LABELS, "facilities": synthetic.list_facilities()}


@app.get("/api/clock")
def get_clock(asof: str | None = None):
    try:
        _, info = clock.resolve_as_of(asof)
    except clock.ClockError as e:
        raise HTTPException(400, str(e))
    return {"clock": info, "earliest": clock.EARLIEST.isoformat(), "recent_window_days": nws_client.RECENT_DAYS,
            "live_tolerance_minutes": int(nws_client.LIVE_TOLERANCE.total_seconds() // 60), "offline": http_cache.offline()}


@app.post("/api/evaluate")
def evaluate(req: EvaluateReq):
    try:
        ctx, rec = workflow.evaluate(req.facility_id, req.as_of)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except clock.ClockError as e:
        raise HTTPException(400, str(e))
    except http_cache.OfflineCacheMiss as e:
        raise HTTPException(503, str(e))
    return workflow.view(ctx, rec)


@app.post("/api/second-opinion")
def second_opinion(ref: EvalRef):
    try:
        ctx = workflow.load(ref.evaluation_id)
    except KeyError:
        raise HTTPException(404, "unknown evaluation_id")

    def run():
        out = agents.run_second_opinion(ctx)
        out["record"] = store.append(ref.evaluation_id, ctx.facility["id"], "second_opinion", out)
        return out
    return _submit("second_opinion", ref.evaluation_id, run)


@app.post("/api/decision")
def decision(req: DecisionReq):
    try:
        payload, rec = workflow.record_decision(req.evaluation_id, req.selected_posture, req.reason, req.decided_by)
    except KeyError:
        raise HTTPException(404, "unknown evaluation_id")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"decision": payload, "record": rec}


@app.post("/api/notifications")
def notifications(ref: EvalRef):
    d = store.latest(ref.evaluation_id, "manager_decision")
    if not d:
        raise HTTPException(409, "A human manager decision must be recorded before notifications can be drafted.")
    ctx = workflow.load(ref.evaluation_id)

    def run():
        out = agents.run_notifications(ctx, d["payload"])
        if out["status"] == "ok":
            out["record"] = store.append(ref.evaluation_id, ctx.facility["id"], "notification_package", out)
        return out
    return _submit("notifications", ref.evaluation_id, run)


@app.get("/api/jobs/{job_id}")
def job(job_id: str):
    with _jobs_lock:
        j = _jobs.get(job_id)
    if not j:
        raise HTTPException(404, "unknown job")
    return j


@app.get("/api/records")
def records(facility_id: str | None = None):
    return {"records": store.list_evaluations(facility_id)}


@app.get("/api/records/{evaluation_id}")
def record(evaluation_id: str):
    try:
        return workflow.reconstruct(evaluation_id)
    except KeyError:
        raise HTTPException(404, "unknown evaluation_id")


@app.get("/")
def index():
    return {"message": "ClearSight API. No dashboard is bundled; interactive docs at /docs"}
