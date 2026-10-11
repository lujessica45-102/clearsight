"""Build closure/replay/nebraska_2019.json from archived NWS products (Iowa Environmental Mesonet).

Event: March 2019 'bomb cyclone' rain-on-frozen-ground flooding, eastern Nebraska (Lincoln / Omaha / Elkhorn).
Build-time only (needs requests, pyshp, shapely). The app itself just reads the JSON.
Run: python build_nebraska_fixture.py
"""
import csv
import datetime as dt
import io
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

import requests
import shapefile
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

OUT = Path(__file__).with_name("nebraska_2019.json")
IEM = "https://mesonet.agron.iastate.edu"
UA = {"User-Agent": "ClosureCall-hackathon-replay-builder/1.0"}
UTC = dt.timezone.utc

# OAX = NWS Omaha/Valley, the forecast office for Lancaster, Douglas, Sarpy, Washington, Dodge, Cass, Saunders counties.
WWA_URL = (f"{IEM}/cgi-bin/request/gis/watchwarn.py?wfo[]=OAX"
           "&year1=2019&month1=3&day1=12&hour1=0&minute1=0"
           "&year2=2019&month2=3&day2=19&hour2=0&minute2=0")
ASOS_URL = (f"{IEM}/cgi-bin/request/asos.py?station=LNK&station=OMA"
            "&data=sknt&data=gust&data=mslp&data=wxcodes&data=vsby&data=metar"
            "&year1=2019&month1=3&day1=13&hour1=0&minute1=0"
            "&year2=2019&month2=3&day2=18&hour2=23&minute2=59"
            "&tz=UTC&format=onlycomma&latlon=yes&missing=null&report_type=3&report_type=4")
NWSTEXT_URL = f"{IEM}/api/1/nwstext/{{pid}}"

# Region of interest: Lincoln, Omaha, Elkhorn, Fremont, Blair and surrounding eastern Nebraska.
REGION = box(-97.5, 40.4, -95.5, 41.9)

EVENT_NAMES = {
    ("FA", "W"): "Flood Warning", ("FA", "A"): "Flood Watch", ("FA", "Y"): "Flood Advisory",
    ("FF", "W"): "Flash Flood Warning", ("FF", "A"): "Flash Flood Watch",
    ("WI", "Y"): "Wind Advisory", ("HW", "W"): "High Wind Warning", ("HW", "A"): "High Wind Watch",
    ("FG", "Y"): "Dense Fog Advisory",
    ("WS", "W"): "Winter Storm Warning", ("WS", "A"): "Winter Storm Watch", ("BZ", "W"): "Blizzard Warning",
    ("WW", "Y"): "Winter Weather Advisory",
    ("TO", "W"): "Tornado Warning", ("TO", "A"): "Tornado Watch",
    ("SV", "W"): "Severe Thunderstorm Warning", ("SV", "A"): "Severe Thunderstorm Watch",
}
# River-forecast-point flood products (phenomena FL) are deliberately NOT included (same as the Michael builder).

# 2019-03-10 was the start of daylight time: CDT = UTC-5. Wed Mar 13, Thu Mar 14, Fri Mar 15 and Mon Mar 18 are weekdays.
SNAPSHOTS = [
    ("2019-03-14T00:00:00Z", "Wed Mar 13, 7:00 PM CDT - evening before; Flood Watch and areal Flood Warnings already in effect"),
    ("2019-03-14T09:00:00Z", "Thu Mar 14, 4:00 AM CDT - the 4 AM decision; heavy rain and snowmelt flooding on frozen ground"),
    ("2019-03-14T16:00:00Z", "Thu Mar 14, 11:00 AM CDT - mid-event; Flash Flood Warning for Omaha/Elkhorn area, wind advisory"),
    ("2019-03-15T09:00:00Z", "Fri Mar 15, 4:00 AM CDT - flood phase; rivers rising, levee-breach flooding, roads cut"),
    ("2019-03-18T12:00:00Z", "Mon Mar 18, 7:00 AM CDT - ongoing flood warning; commute week begins"),
]


def p(s):
    return dt.datetime.strptime(s, "%Y%m%d%H%M").replace(tzinfo=UTC)


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%MZ") if d else None


def get(url, **kw):
    r = requests.get(url, headers=UA, timeout=120, **kw)
    r.raise_for_status()
    return r


def load_wwa():
    z = zipfile.ZipFile(io.BytesIO(get(WWA_URL).content))
    base = next(n[:-4] for n in z.namelist() if n.endswith(".shp"))
    rd = shapefile.Reader(shp=io.BytesIO(z.read(base + ".shp")),
                          dbf=io.BytesIO(z.read(base + ".dbf")),
                          shx=io.BytesIO(z.read(base + ".shx")))
    recs, dropped = [], defaultdict(int)
    for sr in rd.iterShapeRecords():
        d = sr.record.as_dict()
        key = (d["PHENOM"], d["SIG"])
        if key not in EVENT_NAMES:
            dropped["phenomena not in scope (e.g. FL river-forecast flood products)"] += 1
            continue
        issued, expired = p(d["ISSUED"]), p(d["EXPIRED"])
        if issued >= expired:
            dropped["inconsistent ISSUED>=EXPIRED in archive"] += 1
            continue
        geom = shape(sr.shape.__geo_interface__)
        if not geom.intersects(REGION):
            dropped["outside region"] += 1
            continue
        d.update(issued=issued, expired=expired, init_iss=p(d["INIT_ISS"]),
                 init_exp=p(d["INIT_EXP"]), geom=geom)
        recs.append(d)
    return recs, dict(dropped)


def clean_geom(g):
    g = g.simplify(0.004, preserve_topology=True)

    def rnd(o):
        return [rnd(x) for x in o] if isinstance(o, (list, tuple)) else round(o, 4)
    m = mapping(g)
    return {"type": m["type"], "coordinates": rnd(m["coordinates"])}


def fetch_text(pid, cache):
    if pid in cache:
        return cache[pid]
    try:
        t = get(NWSTEXT_URL.format(pid=pid)).text
        t = re.sub(r"\A\s*\d+\s*\n", "", t)
    except Exception:
        t = None
    cache[pid] = t
    return t


def load_asos():
    rows = list(csv.DictReader(io.StringIO(get(ASOS_URL).text)))
    by = defaultdict(list)
    for r in rows:
        r["t"] = dt.datetime.strptime(r["valid"], "%Y-%m-%d %H:%M").replace(tzinfo=UTC)
        by[r["station"]].append(r)
    return by


def fnum(x):
    try:
        return None if x in (None, "", "null") else float(x)
    except ValueError:
        return None


STATIONS = {"LNK": ("KLNK", "Lincoln Municipal Airport"), "OMA": ("KOMA", "Eppley Airfield, Omaha")}


def observations_at(by, T):
    out = []
    for stn, rows in sorted(by.items()):
        prior = [r for r in rows if r["t"] <= T and (T - r["t"]) <= dt.timedelta(minutes=90)]
        if not prior:
            continue
        last = max(prior, key=lambda r: r["t"])
        win = [r for r in rows if T - dt.timedelta(hours=6) <= r["t"] <= T]
        gusts = [g for r in win for g in (fnum(r["gust"]), fnum(r["sknt"])) if g is not None]
        out.append({
            "station": STATIONS[stn][0], "station_note": STATIONS[stn][1],
            "time": last["t"].strftime("%Y-%m-%dT%H:%MZ"),
            "wind_speed_kt": fnum(last["sknt"]), "wind_gust_kt": fnum(last["gust"]),
            "pressure_mb": fnum(last["mslp"]), "visibility_mi": fnum(last["vsby"]),
            "conditions": None if last["wxcodes"] in ("null", "") else last["wxcodes"],
            "max_wind_or_gust_kt_prior_6h": max(gusts) if gusts else None,
            "raw_metar": last["metar"],
            "lon": fnum(last["lon"]), "lat": fnum(last["lat"]),
            "source_url": ASOS_URL,
        })
    return out


def build():
    retrieved = dt.datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    recs, dropped = load_wwa()
    asos = load_asos()
    text_cache, snapshots = {}, []

    for as_of_s, label in SNAPSHOTS:
        T = dt.datetime.strptime(as_of_s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
        groups = defaultdict(list)
        for r in recs:
            if r["issued"] <= T < r["expired"]:
                groups[(r["WFO"], r["PHENOM"], r["SIG"], r["ETN"])].append(r)
        alerts = []
        for (wfo, ph, sig, etn), rs in sorted(groups.items()):
            polys = [r for r in rs if r["GTYPE"] == "P"]
            use = polys or rs
            kind = "polygon" if polys else "county_zone"
            geom = unary_union([r["geom"] for r in use])
            ugcs = sorted({r["NWS_UGC"] for r in rs if r["NWS_UGC"]})
            first = min(rs, key=lambda r: r["issued"])
            pid = first["PROD_ID"]
            body = fetch_text(pid, text_cache)
            desc, prod_info = None, None
            if body and first["init_iss"] <= T:
                desc = body[:1500].strip()
                prod_info = {"pil": pid.split("-")[-1], "issued": iso(first["init_iss"]), "url": NWSTEXT_URL.format(pid=pid)}
            # The archive's end time can be hindsight (early cancellation, later extension). Only the end time stated at
            # original issuance is usable, and only if no extension had happened yet.
            extended = any(r["STATUS"] == "EXT" for r in rs)
            expires = iso(first["init_exp"]) if first["STATUS"] == "NEW" and not extended else None
            alerts.append({
                "id": f"VTEC:{wfo}.{ph}.{sig}.{etn:04d}.2019",
                "event": EVENT_NAMES[(ph, sig)],
                "vtec": {"office": "K" + wfo, "phenomena": ph, "significance": sig, "etn": etn},
                "severity": None, "urgency": None, "certainty": None,
                "classification_note": "CAP severity/urgency/certainty are not in the VTEC archive; "
                                       "derive from vtec.phenomena/significance (prototype mapping).",
                "headline": None, "description": desc, "instruction": None,
                "sent": iso(first["init_iss"]), "effective": iso(first["issued"]),
                "onset": None, "expires": expires,
                "expires_note": None if expires else
                "end time withheld: archive end time is hindsight (cancellation/extension) or a placeholder",
                "sender": "NWS Omaha/Valley NE",
                "areaDesc": "UGC zones: " + ", ".join(ugcs) if ugcs else "Storm-based polygon",
                "ugc_codes": ugcs,
                "geometry": clean_geom(geom), "geometry_kind": kind,
                "text_product": prod_info,
                "source_url": WWA_URL,
            })
        snapshots.append({"as_of": as_of_s, "label": label, "alerts": alerts,
                          "observations": observations_at(asos, T)})

    return {
        "scenario_id": "nebraska_2019",
        "title": "March 2019 bomb cyclone flooding - Eastern Nebraska (Lincoln / Omaha / Elkhorn), March 13-18, 2019",
        "kind": "historical_archive",
        "disclaimer": ("HISTORICAL REPLAY. Every alert, text and observation here is an archived real "
                       "National Weather Service / IEM record from March 2019, selected by time filter and "
                       "replayed. It is NOT live data and must never be presented as a current alert. "
                       "Road closures are not included (no archived 511 data was available)."),
        "facts": {
            "event": "Mid-March 2019 'bomb cyclone' and eastern Nebraska flooding (rain and rapid snowmelt on frozen ground)",
            "bomb_cyclone": "Deepened 24 mb in 15 h, from 994 mb to about 970 mb, on March 12-13, 2019 (NWS Hastings/GID).",
            "weather_window": "From March 12-14 a rapidly deepening low brought heavy rain, warm temperatures and dense fog with rapid "
                              "snow/ice melt; ground was frozen deeper than 2 feet (NWS flood-safety page for Nebraska).",
            "blizzard_note": "Blizzard conditions on the morning of March 14 occurred in central Nebraska (e.g. Ord), per NWS Hastings; "
                             "the OAX archive has NO blizzard or winter storm product covering the Lincoln/Omaha facility locations.",
            "impacts": ["Nearly 50 levees were breached on the Platte, Elkhorn and Missouri Rivers (NWS).",
                        "A Platte River levee breach near Leshara forced the evacuation of NWS Omaha/Valley (NWS).",
                        "Valley and Fremont, NE were cut off from the rest of the state for a time by flooded roads (NWS Central Region).",
                        "About one-third of Offutt Air Force Base was flooded; Interstate 29 south of Omaha remained closed (NWS Central Region)."],
            "weekdays": "Wed Mar 13, Thu Mar 14, Fri Mar 15 and Mon Mar 18, 2019 were all normal work days.",
            "source_urls": ["https://www.weather.gov/gid/march2019flood",
                            "https://www.weather.gov/crh/historic_flooding_2019",
                            "https://www.weather.gov/safety/flood-states-ne"],
        },
        "sources": [
            {"name": "NWS Hastings: Mid-March 2019 Nebraska flooding summary (bomb cyclone facts)",
             "url": "https://www.weather.gov/gid/march2019flood", "retrieved_at": retrieved},
            {"name": "NWS Central Region: 2019 Eastern Nebraska Flooding facts",
             "url": "https://www.weather.gov/crh/historic_flooding_2019", "retrieved_at": retrieved},
            {"name": "NWS: Flooding in Nebraska (March 2019 flood section)",
             "url": "https://www.weather.gov/safety/flood-states-ne", "retrieved_at": retrieved},
            {"name": "IEM archived NWS VTEC watch/warning shapefile (WFO OAX)", "url": WWA_URL, "retrieved_at": retrieved},
            {"name": "IEM archived NWS products text (alert text, per PROD_ID)",
             "url": NWSTEXT_URL.format(pid="<PROD_ID>"), "retrieved_at": retrieved},
            {"name": "IEM archived ASOS observations (KLNK, KOMA)", "url": ASOS_URL, "retrieved_at": retrieved},
        ],
        "build_notes": {"records_dropped": dropped, "region_bbox_lonlat": list(REGION.bounds), "geometry_simplify_deg": 0.004},
        "snapshots": snapshots,
    }


if __name__ == "__main__":
    data = build()
    OUT.write_text(json.dumps(data, separators=(",", ":")))
    print("wrote", OUT, OUT.stat().st_size // 1024, "KB; dropped:", data["build_notes"]["records_dropped"])
