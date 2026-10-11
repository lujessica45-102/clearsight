"""Employee exposure analysis against alert geometry.

Commute exposure is a STRAIGHT-LINE approximation (home -> facility segment tested against alert shapes);
we have no routing data, so it says where a commute may cross a hazard, not the actual road path or travel time.
"""
from datetime import timedelta

from .geo import Area, haversine_km
from .hazards import parse_ts

TRANSIENT_CLASSES = {"tornado", "convective"}   # short-fuse warnings: minutes to ~1h


def alert_interval(alert):
    """(start, end, end_is_known). An unknown end means 'still in effect' (conservative), never an invented expiry."""
    start = parse_ts(alert.get("onset")) or parse_ts(alert.get("effective")) or parse_ts(alert.get("sent"))
    end = parse_ts(alert.get("ends")) or parse_ts(alert.get("expires"))
    return start, end, end is not None


def relevant_alerts(alerts, window_start, window_end):
    """Alerts that overlap the decision window. Short-fuse warnings count only near the window start."""
    out = []
    for a in alerts:
        start, end, _ = alert_interval(a)
        ws, we = window_start, window_end
        if a["hazard_class"] in TRANSIENT_CLASSES:
            we = window_start + timedelta(hours=2)
        if (start is None or start <= we) and (end is None or end >= ws):
            out.append(a)
    return out


def _risk_for(level):
    return "high" if level >= 4 else "elevated" if level == 3 else "low"


def analyze_employees(facility, employees, alerts, window_start, window_end):
    rel = relevant_alerts(alerts, window_start, window_end)
    areas = {a["id"]: Area(a["geometry"]) for a in rel if a.get("geometry")}
    flat, flon = facility["latitude"], facility["longitude"]

    facility_alerts = [a for a in rel if a["id"] in areas and areas[a["id"]].contains(flat, flon)]
    # an alert NWS itself says covers the facility point counts even if our geometry is missing
    ids = {a["id"] for a in facility_alerts}
    for a in rel:
        if a["id"] not in ids and a.get("nws_says_covers_facility_point"):
            facility_alerts.append(a)

    people = []
    for e in employees:
        worst, worst_alert, home_in, route_in = 0, None, False, False
        for a in rel:
            ar = areas.get(a["id"])
            if not ar:
                continue
            h = ar.contains(e["home_lat"], e["home_lon"])
            r = h or ar.crosses_line(e["home_lat"], e["home_lon"], flat, flon)
            if not r:
                continue
            home_in |= h
            route_in |= r
            lvl = a["base_level"] if a["travel_impacting"] else 0
            if a["hazard_class"] == "flood" and lvl <= 3 and a.get("geometry_kind") != "polygon":
                lvl = min(lvl, 2)   # county/zone-wide river-flood products are not evidence of a blocked commute (no polygon, no road data)
            if a["hazard_class"] in TRANSIENT_CLASSES:
                lvl = min(lvl, 3)   # minutes-long warnings can make a commute 'elevated' but never justify closure on their own
            if lvl > worst:
                worst, worst_alert = lvl, a
        risk = _risk_for(worst) if worst else "none"
        people.append({**e, "commute_risk": risk, "home_in_hazard": home_in, "route_crosses_hazard": route_in,
                       "worst_alert_id": worst_alert["id"] if worst_alert else None,
                       "worst_event": worst_alert["event"] if worst_alert else None,
                       "commute_km_straight_line": round(haversine_km(e["home_lat"], e["home_lon"], flat, flon), 1)})

    n = len(people) or 1
    count = lambda pred: sum(1 for p in people if pred(p))
    high = [p for p in people if p["commute_risk"] == "high"]
    elev = [p for p in people if p["commute_risk"] == "elevated"]
    affected = high + elev
    metrics = {
        "workforce": len(people),
        "high_commute_risk": len(high), "elevated_commute_risk": len(elev),
        "low_commute_risk": count(lambda p: p["commute_risk"] == "low"),
        "no_exposure": count(lambda p: p["commute_risk"] == "none"),
        "high_pct": round(100 * len(high) / n, 1), "elevated_pct": round(100 * len(elev) / n, 1),
        "high_or_elevated_pct": round(100 * len(affected) / n, 1),
        "home_in_hazard": count(lambda p: p["home_in_hazard"]),
        "route_crosses_hazard": count(lambda p: p["route_crosses_hazard"]),
        "affected_essential": sum(1 for p in affected if p["essential"]),
        "affected_telework_eligible": sum(1 for p in affected if p["telework_eligible"]),
        "affected_accessibility_need": sum(1 for p in affected if p["accessibility_need"]),
        "affected_neither_essential_nor_telework": sum(1 for p in affected if not p["essential"] and not p["telework_eligible"]),
        "telework_share_of_affected": round(sum(1 for p in affected if p["telework_eligible"]) / len(affected), 2) if affected else None,
        "essential_total": count(lambda p: p["essential"]),
        "telework_eligible_total": count(lambda p: p["telework_eligible"]),
        "accessibility_total": count(lambda p: p["accessibility_need"]),
    }
    by_community = {}
    for p in people:
        c = by_community.setdefault(p["home_community"], {"total": 0, "high": 0, "elevated": 0})
        c["total"] += 1
        if p["commute_risk"] in ("high", "elevated"):
            c[p["commute_risk"]] += 1
    return {
        "metrics": metrics, "facility_alerts": facility_alerts, "relevant_alert_ids": [a["id"] for a in rel],
        "by_community": by_community, "people": people,
        "method_note": "Exposure uses straight-line home->facility segments against alert shapes; no road routing or travel times. Employee data is SYNTHETIC.",
        "geometry_kinds": sorted({a.get("geometry_kind") for a in rel if a.get("geometry_kind")}),
    }
