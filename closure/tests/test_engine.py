"""Deterministic tests. Alerts marked SYNTHETIC TEST FIXTURE are invented geometry used only to exercise rules
(no archived real event covers that case). Tests that query real NWS/IEM data live in test_asof.py (network-marked)."""
import os, sqlite3, tempfile
_tmp = tempfile.mkdtemp()
os.environ["CLEARSIGHT_DECISIONS_DB"] = os.path.join(_tmp, "decisions.db")
os.environ["CLEARSIGHT_FACILITIES_DB"] = os.path.join(_tmp, "facilities.db")

from datetime import datetime, timezone, timedelta
import pytest
from closure import synthetic, hazards, impact, roads, engine, store, workflow, agents, clock


def box(lat0, lat1, lon0, lon1):
    return {"type": "Polygon", "coordinates": [[[lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0]]]}


def alert(event, geom, start, end=None, urgency="Immediate", certainty="Likely", severity="Severe", aid=None):
    a = {"id": aid or f"SYNTHETIC-{event}", "event": event, "headline": f"SYNTHETIC TEST FIXTURE: {event}", "description": "", "instruction": "",
         "severity": severity, "urgency": urgency, "certainty": certainty, "status": "Actual", "message_type": "Alert", "areaDesc": "synthetic",
         "sent": start.isoformat(), "effective": start.isoformat(), "onset": start.isoformat(), "expires": end.isoformat() if end else None,
         "ends": None, "sender": "synthetic", "geometry": geom, "geometry_kind": "polygon", "source": "SYNTHETIC TEST FIXTURE",
         "source_url": None, "retrieved_at": start.isoformat()}
    return hazards._finish(a)


def run(fid, alerts, as_of, mode="live"):
    f = synthetic.get_facility(fid)
    pic = {"mode": mode, "scenario": None, "as_of": as_of.isoformat(), "retrieved_at": as_of.isoformat(), "alerts": alerts, "weather": None,
           "sources": [], "errors": [], "disclaimer": None}
    win = engine.operating_window(f, as_of)
    imp = impact.analyze_employees(f, synthetic.employees_for(fid), alerts, win["window_start"], win["window_end"])
    return engine.evaluate(f, pic, imp, roads.road_conditions(f, "live"), as_of), imp


WED_4AM_CT = datetime(2026, 1, 14, 10, 0, tzinfo=timezone.utc)   # Wednesday 04:00 CST, before opening


def test_synthetic_facilities_are_labelled_and_complete():
    fs = synthetic.list_facilities()
    assert len(fs) == 10 and all(f["synthetic"] for f in fs)
    assert {f["sector"] for f in fs} == {"service_center", "research_lab", "field_office", "headquarters"}
    e = synthetic.employees_for("ne-lincoln-sc")[0]
    assert set(e) >= {"id", "home_lat", "home_lon", "essential", "telework_eligible", "accessibility_need"} and "name" not in e


def test_ne_commutes_blocked_but_facility_unaffected_gives_telework():
    # SYNTHETIC polygon over the communities south of Lincoln only; the facility itself is outside it.
    a = alert("Winter Storm Warning", box(40.55, 40.72, -96.85, -96.40), WED_4AM_CT - timedelta(hours=2), WED_4AM_CT + timedelta(hours=20))
    r, imp = run("ne-lincoln-sc", [a], WED_4AM_CT)
    assert not imp["facility_alerts"], "facility must be outside the alert"
    assert imp["metrics"]["high_pct"] >= 15
    assert r["posture"] in ("telework", "closure") and r["binding_rule"] in ("R3", "R4")
    assert any(x["id"] == "R4" for x in r["rules"])


def test_headquarters_prefers_telework_over_closure_when_most_can_telework():
    a = alert("Winter Storm Warning", box(41.0, 41.45, -96.00, -95.60), WED_4AM_CT - timedelta(hours=2), WED_4AM_CT + timedelta(hours=20))
    r, imp = run("ne-omaha-hq", [a], WED_4AM_CT)
    assert imp["metrics"]["high_pct"] >= 50 and not imp["facility_alerts"]
    assert r["posture"] == "telework" and r["sector_notes"], "closure threshold crossed but HQ telework share should downgrade it"


def test_short_lived_commute_hazard_gives_delayed_arrival():
    opens = datetime(2026, 1, 14, 13, 30, tzinfo=timezone.utc)  # 07:30 CST
    a = alert("Flash Flood Warning", box(40.55, 40.72, -96.85, -96.40), WED_4AM_CT, opens + timedelta(hours=2))
    r, imp = run("ne-lincoln-sc", [a], WED_4AM_CT)
    assert r["posture"] == "delayed_arrival" and r["binding_rule"] == "R5"


def test_tornado_warning_triggers_shelter_in_place_not_closure():
    now = datetime(2026, 4, 15, 18, 0, tzinfo=timezone.utc)  # Wednesday 13:00 CDT, open
    a = alert("Tornado Warning", box(40.7, 40.9, -96.8, -96.6), now - timedelta(minutes=5), now + timedelta(minutes=30))
    r, _ = run("ne-lincoln-sc", [a], now)
    assert any("SHELTER IN PLACE" in x for x in r["immediate_actions"]) and r["posture"] != "closure"


def test_competing_hazards_prioritised_by_severity_urgency_and_exposure():
    now = WED_4AM_CT
    minor = alert("Wind Advisory", box(40.7, 40.9, -96.8, -96.6), now, now + timedelta(hours=12), urgency="Expected", severity="Minor", aid="minor")
    major = alert("Flash Flood Warning", box(40.7, 40.9, -96.8, -96.6), now, now + timedelta(hours=12), aid="major")
    watch = alert("Flood Watch", box(40.7, 40.9, -96.8, -96.6), now, now + timedelta(hours=30), urgency="Future", severity="Moderate", aid="watch")
    ranked = sorted([minor, watch, major], key=lambda a: -a["priority_score"])
    assert [a["id"] for a in ranked] == ["major", "watch", "minor"]
    r, _ = run("ne-lincoln-sc", [minor, watch, major], now)
    assert r["posture"] != "normal" and r["binding_rule"] in ("R2", "R3", "R4", "R5")
    only_minor, _ = run("ne-lincoln-sc", [minor], now)
    assert only_minor["posture"] == "normal", "a minor advisory alone must not change operations"


def test_alert_without_known_end_is_treated_as_still_in_effect():
    a = alert("Hurricane Warning", box(40.7, 40.9, -96.8, -96.6), WED_4AM_CT - timedelta(days=2), None)
    r, imp = run("ne-lincoln-sc", [a], WED_4AM_CT)
    assert imp["facility_alerts"] and r["posture"] == "closure" and r["binding_rule"] == "R1"


def test_agent_cannot_quietly_lower_a_safety_floor():
    a = alert("Hurricane Warning", box(40.7, 40.9, -96.8, -96.6), WED_4AM_CT - timedelta(days=1), None)
    det, _ = run("ne-lincoln-sc", [a], WED_4AM_CT)
    out = agents.reconcile(det, {"recommended_posture": "telework"})
    assert out["posture"] == "closure" and out["agent_downgrade_blocked_by_safety_floor"] and out["agent_disagrees_with_deterministic"]
    up = agents.reconcile({**det, "rules": [], "posture": "normal"}, {"recommended_posture": "closure"})
    assert up["posture"] == "closure" and up["agent_escalated_above_deterministic"]


def test_weekend_evaluation_targets_next_operating_day():
    sat = datetime(2026, 1, 17, 18, 0, tzinfo=timezone.utc)
    w = engine.operating_window(synthetic.get_facility("ne-lincoln-sc"), sat)
    assert w["state"] == "outside_operating_hours" and w["opens_at"].startswith("2026-01-19")


def test_unavailable_road_data_is_explicit_and_never_invented():
    r = roads.road_conditions(synthetic.get_facility("ne-lincoln-sc"), "live")
    assert r["status"] == "unavailable" and r["events"] == [] and "API key" in r["reason"]
    assert roads.road_conditions(synthetic.get_facility("fl-pensacola-sc"), "archive")["status"] == "unavailable"


def test_open_facility_with_short_hazard_holds_staff_instead_of_changing_status():
    now = datetime(2026, 4, 15, 17, 0, tzinfo=timezone.utc)   # Wednesday noon CDT, open
    a = alert("Flash Flood Warning", box(40.55, 40.95, -96.85, -96.40), now - timedelta(hours=1), now + timedelta(hours=2))
    r, _ = run("ne-lincoln-sc", [a], now)
    assert r["posture"] == "normal" and any("HOLD STAFF ON SITE" in x for x in r["immediate_actions"])


def test_zone_wide_flood_warning_is_not_treated_as_blocked_commutes():
    a = alert("Flood Warning", box(40.55, 40.95, -96.85, -96.40), WED_4AM_CT - timedelta(hours=1), WED_4AM_CT + timedelta(hours=40))
    a["geometry_kind"] = "county_zone"
    r, imp = run("ne-lincoln-sc", [a], WED_4AM_CT)
    assert imp["metrics"]["high_or_elevated_pct"] == 0 and r["posture"] == "normal"


def test_open_ended_alerts_lower_confidence_explicitly():
    a = alert("Hurricane Warning", box(40.7, 40.9, -96.8, -96.6), WED_4AM_CT - timedelta(days=2), None)
    r, _ = run("ne-lincoln-sc", [a], WED_4AM_CT)
    assert any("no known end time" in f for f in r["confidence"]["factors"])



# ---- decision log + overrides, using a SYNTHETIC test picture (no network) ---------------------------------
def synthetic_ctx(fid="ne-lincoln-sc", event="Hurricane Warning"):
    a = alert(event, box(40.7, 40.9, -96.8, -96.6), WED_4AM_CT - timedelta(days=1), None)
    f = synthetic.get_facility(fid)
    pic = {"mode": "archive", "scenario": None, "as_of": WED_4AM_CT.isoformat(), "retrieved_at": WED_4AM_CT.isoformat(), "alerts": [a],
           "weather": None, "sources": [], "errors": [], "disclaimer": "SYNTHETIC TEST FIXTURE", "data_source": {"name": "synthetic", "cached": False, "notes": []}}
    return workflow.evaluate_picture(f, pic)


def test_decision_override_requires_reason_and_is_logged_with_intact_chain():
    ctx, _ = synthetic_ctx()
    with pytest.raises(ValueError):
        workflow.record_decision(ctx.evaluation_id, "telework", "  ", "Facility manager")
    d, _ = workflow.record_decision(ctx.evaluation_id, "telework", "Staff already evacuated; telework for continuity.", "Facility manager")
    assert d["is_override"] and d["human_approved"] and d["deterministic_posture"] == "closure"
    rec = workflow.reconstruct(ctx.evaluation_id)
    assert rec["chain_verified"] and [t["type"] for t in rec["timeline"]] == ["evaluation", "manager_decision"]
    assert rec["manager_decision"]["reason"].startswith("Staff already")


def test_decision_log_is_append_only_and_tamper_evident():
    ctx, _ = synthetic_ctx()
    c = sqlite3.connect(os.environ["CLEARSIGHT_DECISIONS_DB"])
    with pytest.raises(sqlite3.DatabaseError):
        c.execute("UPDATE events SET payload='{}' WHERE evaluation_id=?", (ctx.evaluation_id,))
    with pytest.raises(sqlite3.DatabaseError):
        c.execute("DELETE FROM events WHERE evaluation_id=?", (ctx.evaluation_id,))
    assert store.verify_chain()[0]


# ---- fire weather rule R8 (SYNTHETIC polygons) --------------------------------------------------------------
@pytest.mark.parametrize("fid,expect", [("ne-omaha-fo", "ignition"), ("ne-lincoln-lab", "ignition sources"), ("ne-lincoln-sc", "evacuation plan"), ("ne-omaha-hq", "evacuation plan")])
def test_red_flag_warning_gives_sector_specific_actions_without_changing_posture(fid, expect):
    f = synthetic.get_facility(fid)
    a = alert("Red Flag Warning", box(f["latitude"] - 0.3, f["latitude"] + 0.3, f["longitude"] - 0.3, f["longitude"] + 0.3), WED_4AM_CT - timedelta(hours=3), WED_4AM_CT + timedelta(hours=30))
    r, _ = run(fid, [a], WED_4AM_CT)
    assert r["posture"] == "normal" and any(x["id"] == "R8" and x["fired"] for x in r["rules"])
    assert any(x.startswith("FIRE WEATHER") and expect in x for x in r["immediate_actions"])
    assert any("evacuation orders" in x for x in r["confidence"]["factors"]), "must say NWS data has no wildfire evacuation orders"
    assert hazards.classify("Red Flag Warning", "", None) == ("fire", 3) and hazards.classify("Fire Weather Watch", "", None) == ("fire", 2)
