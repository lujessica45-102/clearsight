"""Append-only, hash-chained decision log (SQLite). Nothing is ever updated or deleted.

Each event stores a canonical-JSON payload, its SHA-256, and the previous event's hash, so a record can be
reconstructed and tampering is detectable. Event types: evaluation, second_opinion, manager_decision, notification_package.
"""
import hashlib
import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone

from . import config

_lock = threading.Lock()


def _conn():
    c = sqlite3.connect(config.DECISIONS_DB)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS events (
        seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE NOT NULL, evaluation_id TEXT NOT NULL,
        facility_id TEXT NOT NULL, event_type TEXT NOT NULL, created_at TEXT NOT NULL,
        payload TEXT NOT NULL, sha256 TEXT NOT NULL, prev_sha256 TEXT)""")
    c.execute("CREATE INDEX IF NOT EXISTS ix_eval ON events(evaluation_id)")
    c.execute("""CREATE TRIGGER IF NOT EXISTS no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'append-only'); END""")
    c.execute("""CREATE TRIGGER IF NOT EXISTS no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'append-only'); END""")
    return c


def _canon(obj):
    return json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))


def append(evaluation_id, facility_id, event_type, payload):
    with _lock, _conn() as c:
        prev = c.execute("SELECT sha256 FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        body = _canon(payload)
        sha = hashlib.sha256(((prev["sha256"] if prev else "") + body).encode()).hexdigest()
        eid = uuid.uuid4().hex
        created = datetime.now(timezone.utc).isoformat()
        c.execute("INSERT INTO events(event_id,evaluation_id,facility_id,event_type,created_at,payload,sha256,prev_sha256) VALUES(?,?,?,?,?,?,?,?)",
                  (eid, evaluation_id, facility_id, event_type, created, body, sha, prev["sha256"] if prev else None))
        return {"event_id": eid, "created_at": created, "sha256": sha}


def new_evaluation_id():
    return "ev_" + uuid.uuid4().hex[:12]


def events_for(evaluation_id):
    with _conn() as c:
        rows = c.execute("SELECT * FROM events WHERE evaluation_id=? ORDER BY seq", (evaluation_id,)).fetchall()
    return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]


def latest(evaluation_id, event_type):
    ev = [e for e in events_for(evaluation_id) if e["event_type"] == event_type]
    return ev[-1] if ev else None


def list_evaluations(facility_id=None, limit=30):
    q = "SELECT evaluation_id, facility_id, MIN(created_at) AS first_at, MAX(created_at) AS last_at, group_concat(event_type) AS types FROM events"
    args = []
    if facility_id:
        q += " WHERE facility_id=?"; args.append(facility_id)
    q += " GROUP BY evaluation_id ORDER BY MAX(seq) DESC LIMIT ?"; args.append(limit)
    with _conn() as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]


def verify_chain():
    """Recompute every hash in order; returns (ok, first_bad_seq)."""
    with _conn() as c:
        prev = ""
        for r in c.execute("SELECT seq,payload,sha256 FROM events ORDER BY seq"):
            if hashlib.sha256((prev + r["payload"]).encode()).hexdigest() != r["sha256"]:
                return False, r["seq"]
            prev = r["sha256"]
    return True, None
