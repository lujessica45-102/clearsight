"""ClearSight API + dashboard host.   Run from the repo root:  uvicorn closure.api:app --port 8000"""
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import config, synthetic, hazards, workflow, store, agents
from .sectors import SECTORS, POSTURE_LABELS

app = FastAPI(title="ClearSight decision support")
_pool = ThreadPoolExecutor(4)
_jobs, _jobs_lock = {}, threading.Lock()


class EvaluateReq(BaseModel):
    facility_id: str
    mode: str = "live"                 # "live" | "replay"
    scenario_id: str | None = None
    snapshot_index: int = 0


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


@app.get("/api/replay/scenarios")
def scenarios():
    return hazards.list_replay_scenarios()


@app.post("/api/evaluate")
def evaluate(req: EvaluateReq):
    try:
        ctx, rec = workflow.evaluate(req.facility_id, req.mode, req.scenario_id, req.snapshot_index)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except IndexError:
        raise HTTPException(400, "snapshot_index out of range")
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
