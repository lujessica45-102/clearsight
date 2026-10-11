"""Decision history for the "past decisions in similar conditions" panel, stored in Akamai Object Storage.

Runs Rithvika's rule engine (closure/) at every archived moment of both real storms in closure/replay:
  - Hurricane Michael 2018 (5 moments) x Jessica's 25 Florida offices
  - Nebraska 2019 floods (5 moments) x Rithvika's 5 Nebraska facilities (closure/synthetic.py)
Each decision is hash-chained (sha256 of previous hash + record), like closure/store.py.

  python -m backend.history            build frontend/src/history.json (saved copy for the website)
  python -m backend.history --upload   also store every record + an index in the Akamai bucket (needs OBJ_* in .env)
"""
import hashlib, json, sys
from datetime import datetime, timezone
from backend.decide import ROOT, evaluate as _unused, synthetic_employees, to_engine_facility  # noqa: F401
from closure import hazards, engine, roads, synthetic
from closure import impact as impact_mod
from closure.sectors import POSTURE_LABELS

STORMS = [("michael_2018", "Hurricane Michael 2018"), ("nebraska_2019", "Nebraska floods 2019")]
NOT_COVERED = "No warning over the office"


def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)


def florida_sites():
    for o in json.load(open(ROOT / "backend" / "florida_facilities.json")):
        emps = synthetic_employees(o)
        yield to_engine_facility(o, emps), emps


def nebraska_sites():
    for fid, (_, name, sector, lat, lon, tz, (op, cl), n, _w) in synthetic.facility_meta().items():
        if not fid.startswith("ne-"):
            continue
        emps = synthetic.employees_for(fid)
        yield {"id": fid, "name": name, "sector": sector, "latitude": lat, "longitude": lon, "timezone": tz,
               "opening_time": op, "closing_time": cl, "state": "NE", "headcount": n}, emps


def build():
    records, prev = [], ""
    for storm, storm_name in STORMS:
        n_snaps = len(json.load(open(ROOT / "closure" / "replay" / f"{storm}.json"))["snapshots"])
        sites = list(florida_sites() if storm == "michael_2018" else nebraska_sites())
        for i in range(n_snaps):
            pic = hazards.replay_picture(storm, i)
            as_of = hazards.parse_ts(pic["as_of"])
            for fac, emps in sites:
                win = engine.operating_window(fac, as_of)
                imp = impact_mod.analyze_employees(fac, emps, pic["alerts"], win["window_start"], win["window_end"])
                det = engine.evaluate(fac, pic, imp, roads.road_conditions(fac, "replay"), as_of)
                top = max(imp["facility_alerts"], key=lambda a: (a["base_level"], a["priority_score"]), default=None)
                b = next((r for r in det["rules"] if r["id"] == det["binding_rule"]), None)
                rec = {
                    "case_id": f"{storm}-{i}-{fac['id']}", "storm": storm, "storm_name": storm_name,
                    "moment": i, "as_of": pic["as_of"], "moment_label": (pic["scenario"].get("label") or "").split(" - ")[0],
                    "facility_id": fac["id"], "facility_name": fac["name"], "sector": fac["sector"], "state": fac["state"],
                    "hazard": top["event"] if top else NOT_COVERED, "hazard_level": top["base_level"] if top else 0,
                    "exposed_pct": imp["metrics"]["high_or_elevated_pct"], "workforce": imp["metrics"]["workforce"],
                    "posture": det["posture"], "posture_label": POSTURE_LABELS[det["posture"]],
                    "binding_rule": b["id"] if b else None, "binding_name": b["name"] if b else None,
                    "confidence": det["confidence"]["level"],
                }
                rec["sha256"] = hashlib.sha256((prev + canon(rec)).encode()).hexdigest()
                rec["prev_sha256"] = prev or None
                prev = rec["sha256"]
                records.append(rec)
    return records


def main():
    records = build()
    index = {"generated_at": datetime.now(timezone.utc).isoformat(), "count": len(records),
             "chain": "sha256(previous sha256 + canonical JSON of the record)", "records": records, "storage": None}
    if "--upload" in sys.argv:
        import evidence   # Akamai Object Storage client (loads .env)
        for r in records:
            evidence._s3.put_object(Bucket=evidence._BUCKET, Key=f"history/{r['case_id']}.json",
                                    Body=json.dumps(r, indent=1).encode(), ContentType="application/json")
        index["storage"] = {"provider": "Akamai Object Storage", "bucket": evidence._BUCKET,
                            "endpoint": evidence._s3.meta.endpoint_url, "prefix": "history/",
                            "uploaded_at": datetime.now(timezone.utc).isoformat()}
        evidence._s3.put_object(Bucket=evidence._BUCKET, Key="history/index.json",
                                Body=json.dumps(index).encode(), ContentType="application/json")
        print(f"Uploaded {len(records)} records + index to {evidence._BUCKET}/history/")
    json.dump(index, open(ROOT / "frontend" / "src" / "history.json", "w"))
    by = {}
    for r in records:
        by.setdefault(r["hazard"], {}).setdefault(r["posture"], 0)
        by[r["hazard"]][r["posture"]] += 1
    for h, c in by.items():
        print(f"{h:32} {c}")


if __name__ == "__main__":
    main()
