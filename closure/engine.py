"""Deterministic recommendation engine.

All numeric thresholds are visible in the returned `rules` list with their basis. Where a rule rests on an NWS
product classification that is stated; where it is a prototype assumption it is labelled PROTOTYPE ASSUMPTION
(these are NOT official USDA/OPM policy). Postures use OPM operating-status language.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .hazards import parse_ts
from .impact import alert_interval, TRANSIENT_CLASSES, relevant_alerts
from .sectors import SECTORS, POSTURE_LABELS, POSTURE_RANK

ASSUMPTION = "PROTOTYPE ASSUMPTION (not official USDA/OPM policy)"
HOURS_PERSISTENT = 4


def operating_window(facility, as_of):
    tz = ZoneInfo(facility["timezone"])
    local = as_of.astimezone(tz)
    oh, om = map(int, facility["opening_time"].split(":"))
    ch, cm = map(int, facility["closing_time"].split(":"))
    d = local.date()
    while True:
        if d.weekday() < 5:
            open_dt = datetime(d.year, d.month, d.day, oh, om, tzinfo=tz)
            close_dt = datetime(d.year, d.month, d.day, ch, cm, tzinfo=tz)
            if local < close_dt:
                break
        d += timedelta(days=1)
    if open_dt <= local < close_dt:
        state = "open"
    elif d == local.date():
        state = "before_open"
    else:
        state = "outside_operating_hours"
    start = max(as_of, open_dt.astimezone(timezone.utc))
    return {"state": state, "local_time": local.isoformat(), "timezone": facility["timezone"],
            "opens_at": open_dt.isoformat(), "closes_at": close_dt.isoformat(),
            "window_start": start, "window_end": close_dt.astimezone(timezone.utc),
            "hours_to_open": round(max(0, (open_dt.astimezone(timezone.utc) - as_of).total_seconds() / 3600), 1)}


def _rule(rid, name, metric, value, threshold, op, fired, posture, basis, why):
    margin = None
    if isinstance(value, (int, float)) and isinstance(threshold, (int, float)):
        margin = round(value - threshold, 1)
    return {"id": rid, "name": name, "metric": metric, "value": value, "threshold": threshold, "comparator": op,
            "fired": fired, "posture_if_fired": posture, "margin": margin, "basis": basis, "why_this_threshold": why}


def evaluate(facility, picture, impact, roads, as_of=None):
    as_of = as_of or parse_ts(picture["as_of"])
    win = operating_window(facility, as_of)
    sector = SECTORS[facility["sector"]]
    P = sector["params"]
    m = impact["metrics"]
    fac_alerts = impact["facility_alerts"]
    rules, actions = [], []

    def start_of(a):
        return alert_interval(a)[0]

    def end_of(a):
        return alert_interval(a)[1]

    # R1 catastrophic hazard over the facility
    cat = [a for a in fac_alerts if a["base_level"] >= 5]
    rules.append(_rule("R1", "Catastrophic hazard over facility", "highest hazard level at facility (1-5)",
                       max([a["base_level"] for a in fac_alerts], default=0), 5, ">=", bool(cat), "closure",
                       "NWS classification: Hurricane/Storm Surge/Extreme Wind Warning, or flash-flood/tornado emergency wording. "
                       "Operating while one covers the facility is treated as life-threatening. Level mapping is a " + ASSUMPTION,
                       "Employees should not be asked to commute into, or occupy, a facility under a catastrophic-class warning."))

    # R2 sustained warning-level hazard (non-short-fuse) over the facility
    sust = [a for a in fac_alerts if a["base_level"] == 4 and a["hazard_class"] not in TRANSIENT_CLASSES]
    active_sust = [a for a in sust if (start_of(a) is None or start_of(a) <= win["window_start"])]
    later_sust = [a for a in sust if a not in active_sust]
    r2_posture, r2_fired = None, False
    if active_sust:
        ends = [end_of(a) for a in active_sust if end_of(a)]
        hrs = round((max(ends) - win["window_start"]).total_seconds() / 3600, 1) if ends else None
        clears_soon = hrs is not None and hrs <= HOURS_PERSISTENT
        r2_fired = True
        r2_posture = (None if win["state"] == "open" else "delayed_arrival") if clears_soon else "telework"
        r2_val = hrs
    elif later_sust:
        r2_fired, r2_posture, r2_val = True, "early_dismissal", None
    else:
        r2_val = None
    rules.append(_rule("R2", "Sustained warning-level hazard over facility", "hours the warning persists into the operating window",
                       r2_val, HOURS_PERSISTENT, "<= delays / > telework; arrives mid-day -> early dismissal", r2_fired, r2_posture,
                       "NWS Warning-class product (flash flood, winter storm/ice/blizzard, tropical storm warning) covering the facility. "
                       f"The {HOURS_PERSISTENT}h persistence cut-off is a " + ASSUMPTION,
                       "A hazard that clears within a few hours justifies a delay; one that persists makes commuting unreasonable; one arriving mid-day calls for an early release."))

    # R6 short-fuse warning (tornado / severe thunderstorm) over the facility
    transient = [a for a in fac_alerts if a["hazard_class"] in TRANSIENT_CLASSES and a["base_level"] >= 3
                 and (start_of(a) is None or start_of(a) <= win["window_start"] + timedelta(hours=2))]
    rules.append(_rule("R6", "Short-fuse warning over facility", "tornado / severe thunderstorm warnings covering facility",
                       len(transient), 1, ">=", bool(transient), "delayed_arrival" if win["state"] != "open" else None,
                       "NWS Tornado / Severe Thunderstorm Warning. Short-fuse warnings (minutes-1h) trigger shelter-in-place, not a status change. " + ASSUMPTION,
                       "Closing for a warning that expires in under an hour is disproportionate; protecting people in the building right now is not."))
    if transient:
        actions.append("SHELTER IN PLACE: move everyone on site to interior rooms / designated shelter now; do not send staff outside or on the road until the warning expires, then reassess.")

    # workforce rules
    high_pct, tot_pct = m["high_pct"], m["high_or_elevated_pct"]
    travel_alerts = [a for a in relevant_alerts([a for a in picture["alerts"] if a["travel_impacting"]],
                                                win["window_start"], win["window_end"]) if a["base_level"] >= 3]
    ends = [end_of(a) for a in travel_alerts if end_of(a)]
    clears_in = round((max(ends) - win["window_start"]).total_seconds() / 3600, 1) if ends else None
    short = clears_in is not None and clears_in <= HOURS_PERSISTENT
    rules.append(_rule("R3", "Workforce commute exposure -> closure", "% workforce with HIGH commute risk (home/route inside a Warning-level travel hazard)",
                       high_pct, P["closure_exposed_pct"], ">=", high_pct >= P["closure_exposed_pct"] and not short, "closure",
                       f"Sector '{facility['sector']}' parameter; only when the hazard persists beyond {HOURS_PERSISTENT}h of opening or its end is unknown. " + ASSUMPTION,
                       sector["rationale"]))
    rules.append(_rule("R4", "Workforce commute exposure -> unscheduled leave/telework", "% workforce with HIGH or ELEVATED commute risk",
                       tot_pct, P["telework_exposed_pct"], ">=", tot_pct >= P["telework_exposed_pct"] and not short, "telework",
                       f"Sector '{facility['sector']}' parameter; applies when the hazard persists beyond {HOURS_PERSISTENT}h of opening or its end is unknown (clears_in={clears_in}h). " + ASSUMPTION,
                       "When a sizeable share of staff face a hazardous commute, voluntary leave/telework removes them from harm without a formal closure."))
    rules.append(_rule("R5", "Workforce commute exposure -> delayed arrival", "% workforce with HIGH or ELEVATED commute risk",
                       tot_pct, P["delay_exposed_pct"], ">=", tot_pct >= P["delay_exposed_pct"] and short and win["state"] != "open", "delayed_arrival",
                       f"Sector '{facility['sector']}' parameter; hazard must clear within {HOURS_PERSISTENT}h of opening (clears_in={clears_in}h) and the facility must not already be open. " + ASSUMPTION,
                       "A short-lived commute hazard (e.g. morning ice or fog) is best handled by delaying arrival until it clears."))

    if win["state"] == "open" and short and tot_pct >= P["delay_exposed_pct"]:
        actions.append(f"HOLD STAFF ON SITE: {m['high_commute_risk'] + m['elevated_commute_risk']} employees ({tot_pct}%) have a hazardous commute until about {clears_in}h from now; "
                       "avoid sending them out until the warning clears, then release in stages.")

    # R7 roads
    if roads["status"] == "ok":
        closures = [e for e in roads["events"] if e["full_closure"]]
        rules.append(_rule("R7", "Verified road closures near facility", "full road closures within radius", len(closures), 1, ">=",
                           None, None, f"{roads['source']} (live feed). Informational: not yet used to change posture.", "Closures can isolate employees even outside an alert polygon."))
    else:
        rules.append(_rule("R7", "Verified road closures near facility", "full road closures within radius", None, None, "n/a",
                           None, None, f"NOT EVALUATED: {roads['reason']}", "Commute safety is inferred from weather-alert geometry only."))

    # R8 fire weather over the facility: ACTION-ONLY (never changes the posture)
    fire = [a for a in fac_alerts if a["hazard_class"] == "fire"]
    rules.append(_rule("R8", "Fire-weather alert over facility", "fire-weather alerts (Red Flag Warning / Fire Weather Watch / Fire Warning) covering facility",
                       len(fire), 1, ">=", bool(fire), None,
                       "NWS fire-weather products describe dangerous burning CONDITIONS, not an actual fire. Action-only rule, no posture change. " + ASSUMPTION,
                       "Fire weather rarely closes an office by itself, but sites should prepare and field work with ignition risk should stop."))
    if fire:
        actions.append(f"FIRE WEATHER ({', '.join(sorted({a['event'] for a in fire}))}): " + sector["fire_actions"])

    # choose posture
    fired = [r for r in rules if r["fired"] and r["posture_if_fired"]]
    posture, binding = "normal", None
    for r in fired:
        if POSTURE_RANK[r["posture_if_fired"]] > POSTURE_RANK[posture]:
            posture, binding = r["posture_if_fired"], r
    notes = []
    share = P["prefer_telework_over_closure_telework_share"]
    if posture == "closure" and binding and binding["id"] == "R3" and share and (m["telework_share_of_affected"] or 0) >= share:
        notes.append(f"Closure threshold R3 was crossed but {int(100 * m['telework_share_of_affected'])}% of affected staff can telework (sector rule >= {int(100 * share)}%), "
                     "so the posture is telework with continuity of operations instead of closure. The facility itself is not under a catastrophic hazard.")
        posture = "telework"

    if posture != "normal":
        actions.append(sector["playbook"][posture])
    if m["essential_total"] and posture in ("telework", "closure", "early_dismissal"):
        actions.append(f"Essential personnel: {m['essential_total']} flagged essential; {m['affected_essential']} of them have exposed commutes. Confirm coverage plan before releasing staff.")
    if m["affected_accessibility_need"]:
        actions.append(f"{m['affected_accessibility_need']} affected employee(s) have accessibility needs: arrange individual check-ins / transport.")

    # alternatives
    alternatives = []
    for p in ["normal", "delayed_arrival", "telework", "early_dismissal", "closure"]:
        if p == posture:
            continue
        if POSTURE_RANK[p] > POSTURE_RANK[posture]:
            cand = [r for r in rules if r["posture_if_fired"] == p]
            why = "; ".join(f"{r['id']}: {r['metric']} = {r['value']} (needs {r['comparator']} {r['threshold']})" for r in cand if not r["fired"]) or "no rule supports this level"
            alternatives.append({"posture": p, "verdict": "not warranted", "why": why})
        else:
            alternatives.append({"posture": p, "verdict": "insufficient", "why": f"Fired rules ({', '.join(r['id'] for r in fired)}) require at least {posture}."})

    # confidence (qualitative, explicit factors; NOT a calibrated probability)
    factors, score = [], 3
    top = max(fac_alerts + travel_alerts, key=lambda a: a["priority_score"], default=None)
    if not picture["alerts"] and not picture["errors"]:
        factors.append("+ NWS reports no relevant active alerts for this area at retrieval time.")
    if top and top.get("certainty") in ("Possible", "Unlikely"):
        score -= 1; factors.append(f"- Top hazard '{top['event']}' has certainty '{top['certainty']}'.")
    elif top:
        cert = top.get("certainty") or "certainty not in archive"
        urg = top.get("urgency") or "urgency not in archive"
        factors.append(f"+ Top hazard '{top['event']}' ({cert}, {urg}).")
    if picture["mode"] in ("recent", "archive") and not picture["alerts"]:
        score -= 1
        factors.append("- Only archived NWS alerts are represented; damage, power, road and wildfire conditions are NOT, so 'no alerts' does not mean 'safe'.")
    if any(a["hazard_class"] == "fire" for a in picture["alerts"]):
        score -= 0.5
        factors.append("- Wildfire evacuation orders, fire perimeters and smoke closures are NOT in NWS alert data; a fire-weather alert signals dangerous conditions, not a confirmed fire.")
    if roads["status"] != "ok" and (travel_alerts or fac_alerts):
        score -= 1; factors.append("- Road closure data unavailable; commute risk inferred from alert geometry only.")
    if "county_zone" in impact["geometry_kinds"]:
        factors.append("- Some alerts use county/zone shapes, which overstate the true threatened area.")
        score -= 0.5
    if m["high_or_elevated_pct"] >= 90 and m["workforce"] >= 10:
        score -= 0.5
        factors.append(f"- {m['high_or_elevated_pct']}% of the workforce falls inside the alert shapes: broad areal polygons likely overstate how many people truly cannot commute.")
    open_ended = [a for a in impact["facility_alerts"] + travel_alerts if alert_interval(a)[1] is None]
    if open_ended:
        score -= 0.5
        factors.append(f"- {len({a['id'] for a in open_ended})} relevant alert(s) have no known end time and are treated as still in effect (conservative).")
    if picture["errors"]:
        score -= 1; factors.append("- Data retrieval errors: " + "; ".join(picture["errors"]))
    factors.append("- Employee locations are synthetic; real HR data would be needed for a live deployment.")
    confidence = {"level": "High" if score >= 2.5 else "Moderate" if score >= 1.5 else "Low", "factors": factors,
                  "note": "Qualitative assessment of evidence quality; not a calibrated probability."}

    # sensitivity
    sens = []
    n = m["workforce"]
    for r in rules:
        if r["id"] in ("R3", "R4", "R5") and not r["fired"] and isinstance(r["value"], (int, float)):
            need = max(0, round((r["threshold"] - r["value"]) / 100 * n + 0.49))
            if need and POSTURE_RANK[r["posture_if_fired"]] > POSTURE_RANK[posture]:
                sens.append({"change": f"{need} more employee(s) with hazardous commutes ({r['metric'].split(' (')[0]} reaching {r['threshold']}%)",
                             "would_recommend": r["posture_if_fired"]})
    if posture != "normal" and binding:
        sens.append({"change": f"The hazard driving {binding['id']} is cancelled, downgraded or expires before the operating window",
                     "would_recommend": "normal or a lower posture"})
    if not fac_alerts or max(a["base_level"] for a in fac_alerts) < 4:
        sens.append({"change": "A Warning-level alert (or catastrophic Hurricane/Storm Surge Warning) is issued for the facility area", "would_recommend": "early dismissal, telework or closure per rules R1/R2"})
    if roads["status"] != "ok":
        sens.append({"change": "Verified full road closures on commute corridors become available", "would_recommend": "possible escalation (R7 currently informational)"})

    # evidence
    evidence = []
    for a in picture["alerts"]:
        evidence.append({"type": "nws_alert", "id": a["id"], "event": a["event"], "hazard_class": a["hazard_class"], "level": a["base_level"],
                         "severity": a["severity"], "urgency": a["urgency"], "certainty": a["certainty"], "headline": a["headline"],
                         "issued_sent": a["sent"], "effective": a["effective"], "onset": a["onset"], "expires": a["expires"],
                         "retrieved_at": a["retrieved_at"], "source": a["source"], "source_url": a["source_url"],
                         "geometry_kind": a["geometry_kind"], "covers_facility": a["id"] in {x["id"] for x in fac_alerts},
                         "used_in_decision": a["id"] in set(impact["relevant_alert_ids"])})
    w = picture.get("weather") or {}
    if w.get("observation"):
        evidence.append({"type": "observation", "observed_at": w["observation"].get("timestamp") or w["observation"].get("time"),
                         "retrieved_at": picture["retrieved_at"], "data": w["observation"], "source": picture["sources"][:1]})
    evidence.append({"type": "roads", "status": roads["status"], "reason": roads["reason"], "source": roads["source"]})
    evidence.append({"type": "employees", "note": impact["method_note"], "metrics": m})

    if posture == "normal" and not fired:
        just = (f"No Warning-level hazard covers {facility['name']} during the {win['state'].replace('_', ' ')} window and only "
                f"{tot_pct}% of the synthetic workforce has an exposed commute (thresholds: delay {P['delay_exposed_pct']}%, telework {P['telework_exposed_pct']}%). Normal operations are supported; keep monitoring.")
    else:
        just = (f"{POSTURE_LABELS[posture]} is recommended for {facility['name']} because rule {binding['id'] if binding else '-'} "
                f"({binding['name'] if binding else ''}) was crossed. {m['high_commute_risk']} of {n} employees ({high_pct}%) have a high-risk commute and "
                f"{m['elevated_commute_risk']} more are elevated. " + " ".join(notes)).strip()

    return {
        "facility_id": facility["id"], "sector": facility["sector"], "mode": picture["mode"],
        "evaluated_at": datetime.now(timezone.utc).isoformat(), "as_of": as_of.isoformat(),
        "operating_context": {k: v for k, v in win.items() if k not in ("window_start", "window_end")} | {
            "decision_window_start": win["window_start"].isoformat(), "decision_window_end": win["window_end"].isoformat()},
        "posture": posture, "posture_label": POSTURE_LABELS[posture], "binding_rule": binding["id"] if binding else None,
        "rules": rules, "alternatives_considered": alternatives, "immediate_actions": actions, "sector_notes": notes,
        "sector_playbook": sector["playbook"], "confidence": confidence, "sensitivity": sens, "justification": just,
        "evidence": evidence, "assumptions": f"All numeric thresholds not tied to an NWS product class are a {ASSUMPTION}. Human decision-maker has final authority.",
        "status": "DRAFT_RECOMMENDATION_NOT_APPROVED",
    }
