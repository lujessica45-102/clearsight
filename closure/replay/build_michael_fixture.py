"""Build closure/replay/michael_2018.json from archived NWS products (Iowa Environmental Mesonet).

Build-time only (needs requests, pyshp, shapely). The app itself just reads the JSON.
Run: python build_michael_fixture.py
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

OUT = Path(__file__).with_name("michael_2018.json")
IEM = "https://mesonet.agron.iastate.edu"
UA = {"User-Agent": "ClosureCall-hackathon-replay-builder/1.0"}
UTC = dt.timezone.utc

WWA_URL = (f"{IEM}/cgi-bin/request/gis/watchwarn.py?wfo[]=TAE&wfo[]=MOB"
           "&year1=2018&month1=10&day1=8&hour1=0&minute1=0"
           "&year2=2018&month2=10&day2=12&hour2=0&minute2=0")
HLS_URL = (f"{IEM}/cgi-bin/afos/retrieve.py?pil=HLS{{wfo}}"
           "&sdate=2018-10-08T00:00Z&edate=2018-10-12T00:00Z&fmt=text&limit=100")
ASOS_URL = (f"{IEM}/cgi-bin/request/asos.py?station=ECP&station=TLH&station=PNS"
            "&data=sknt&data=gust&data=mslp&data=wxcodes&data=vsby&data=metar"
            "&year1=2018&month1=10&day1=9&hour1=0&minute1=0"
            "&year2=2018&month2=10&day2=11&hour2=23&minute2=59"
            "&tz=UTC&format=onlycomma&latlon=yes&missing=null&report_type=3&report_type=4")
NWSTEXT_URL = f"{IEM}/api/1/nwstext/{{pid}}"

# Region of interest: Pensacola, Panama City, Tallahassee and surrounding Panhandle/Big Bend.
REGION = box(-88.0, 29.2, -83.0, 31.2)

EVENT_NAMES = {
    ("HU", "W"): "Hurricane Warning", ("HU", "A"): "Hurricane Watch",
    ("SS", "W"): "Storm Surge Warning", ("SS", "A"): "Storm Surge Watch",
    ("TR", "W"): "Tropical Storm Warning", ("TR", "A"): "Tropical Storm Watch",
    ("EW", "W"): "Extreme Wind Warning", ("TO", "A"): "Tornado Watch",
    ("TO", "W"): "Tornado Warning", ("FF", "W"): "Flash Flood Warning",
    ("FF", "A"): "Flash Flood Watch", ("CF", "Y"): "Coastal Flood Advisory",
    ("WI", "Y"): "Wind Advisory", ("FA", "W"): "Flood Warning", ("FA", "Y"): "Flood Advisory",
}
TROPICAL = {"HU", "SS", "TR"}

SNAPSHOTS = [
    ("2018-10-09T17:00:00Z", "Tue Oct 9, 12:00 PM CDT - ~24h before landfall; watches/warnings in effect"),
    ("2018-10-10T01:00:00Z", "Tue Oct 9, 8:00 PM CDT - evening before landfall"),
    ("2018-10-10T09:00:00Z", "Wed Oct 10, 4:00 AM CDT - the 4 AM closure decision; ~8h before landfall"),
    ("2018-10-10T17:30:00Z", "Wed Oct 10, 12:30 PM CDT - landfall near Tyndall AFB / Mexico Beach"),
    ("2018-10-11T12:00:00Z", "Thu Oct 11, 7:00 AM CDT - aftermath"),
]


def p(s):
    return dt.datetime.strptime(s, "%Y%m%d%H%M").replace(tzinfo=UTC)


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%MZ") if d else None


def get(url, **kw):
    r = requests.get(url, headers=UA, timeout=90, **kw)
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
            dropped["phenomena not in scope"] += 1
            continue
        ugc = d["NWS_UGC"] or ""
        if ugc[2:3] == "Z" and ugc[:2] in ("GM", "AM", "PZ", "PH", "PK"):
            dropped["marine zone"] += 1
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


def parse_hls(wfo):
    txt = get(HLS_URL.format(wfo=wfo)).text
    parts = re.split(r"(?m)^(?=WTUS\d\d K%s \d{6})" % wfo, txt)
    out = []
    for part in parts:
        m = re.match(r"WTUS\d\d K%s (\d{2})(\d{2})(\d{2})" % wfo, part)
        if not m:
            continue
        day, hh, mm = map(int, m.groups())
        out.append({"issued": dt.datetime(2018, 10, day, hh, mm, tzinfo=UTC), "text": part.strip()})
    return sorted(out, key=lambda x: x["issued"])


def hls_excerpt(prod):
    t = prod["text"]
    title = re.search(r"(?m)^(.*Local Statement Advisory Number \d+)", t)
    bold = re.search(r"\*\*(.+?)\*\*", t)
    i_new = t.find("NEW INFORMATION")
    i_act = t.find("PRECAUTIONARY/PREPAREDNESS ACTIONS")
    desc = t[i_new:i_act if i_act > i_new else None].strip()[:2500] if i_new >= 0 else None
    instr = None
    if i_act >= 0:
        instr = re.sub(r"\n{3,}", "\n\n", t[i_act:i_act + 1400]).strip()
    headline = None
    if title:
        headline = title.group(1).strip() + (" - " + bold.group(1).strip() if bold else "")
    return headline, desc, instr


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
            "station": {"ECP": "KECP", "TLH": "KTLH", "PNS": "KPNS"}[stn],
            "station_note": {"ECP": "Northwest Florida Beaches Intl (Panama City area)",
                             "TLH": "Tallahassee Intl", "PNS": "Pensacola Intl"}[stn],
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
    hls = {w: parse_hls(w) for w in ("TAE", "MOB")}
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
            tropical = ph in TROPICAL
            headline = desc = instr = None
            prod_info = None
            if tropical:
                cands = [h for h in hls[wfo] if h["issued"] <= T]
                if cands:
                    h = cands[-1]
                    headline, desc, instr = hls_excerpt(h)
                    prod_info = {"pil": f"HLS{wfo}", "issued": iso(h["issued"]),
                                 "url": HLS_URL.format(wfo=wfo)}
            else:
                pid = first["PROD_ID"]
                body = fetch_text(pid, text_cache)
                if body and first["init_iss"] <= T:
                    desc = body[:1500].strip()
                    prod_info = {"pil": pid.split("-")[-1], "issued": iso(first["init_iss"]),
                                 "url": NWSTEXT_URL.format(pid=pid)}
            expires = None
            if not tropical and first["STATUS"] == "NEW":
                expires = iso(first["init_exp"])
            alerts.append({
                "id": f"VTEC:{wfo}.{ph}.{sig}.{etn:04d}.2018",
                "event": EVENT_NAMES[(ph, sig)],
                "vtec": {"office": "K" + wfo, "phenomena": ph, "significance": sig, "etn": etn},
                "severity": None, "urgency": None, "certainty": None,
                "classification_note": "CAP severity/urgency/certainty are not in the VTEC archive; "
                                       "derive from vtec.phenomena/significance (prototype mapping).",
                "headline": headline, "description": desc, "instruction": instr,
                "sent": iso(first["init_iss"]), "effective": iso(first["issued"]),
                "onset": None, "expires": expires,
                "expires_note": None if expires else
                "end time withheld: archive end time is hindsight (cancellation) or a placeholder",
                "sender": "NWS " + {"TAE": "Tallahassee FL", "MOB": "Mobile AL"}[wfo],
                "areaDesc": "UGC zones: " + ", ".join(ugcs) if ugcs else "Storm-based polygon",
                "ugc_codes": ugcs,
                "geometry": clean_geom(geom), "geometry_kind": kind,
                "text_product": prod_info,
                "source_url": WWA_URL,
            })
        snapshots.append({"as_of": as_of_s, "label": label, "alerts": alerts,
                          "observations": observations_at(asos, T)})

    return {
        "scenario_id": "michael_2018",
        "title": "Hurricane Michael - Florida Panhandle, October 9-11, 2018",
        "kind": "historical_archive",
        "disclaimer": ("HISTORICAL REPLAY. Every alert, text and observation here is an archived real "
                       "National Weather Service / IEM record from October 2018, selected by time filter and "
                       "replayed. It is NOT live data and must never be presented as a current alert. "
                       "Road closures are not included (no archived 511 data was available)."),
        "facts": {
            "storm": "Hurricane Michael (AL142018), 7-11 October 2018",
            "landfall_utc": "2018-10-10T17:30Z (approx.; 12:30 PM CDT, Wednesday)",
            "landfall_location": "Near Tyndall Air Force Base / Mexico Beach, Florida (SE of Panama City)",
            "landfall_intensity": "Category 5, estimated 140 kt (~160 mph) maximum sustained winds; "
                                  "919 mb central pressure",
            "impacts": "16 direct US deaths, about $25 billion damage (NHC TCR)",
            "storm_surge": "6-9 ft AGL near Tyndall AFB, 4-6 ft around Panama City/St. Andrew Bay "
                           "(NHC TCR)",
            "source_urls": ["https://www.nhc.noaa.gov/data/tcr/AL142018_Michael.pdf"],
        },
        "sources": [
            {"name": "NHC Tropical Cyclone Report AL142018 (landfall facts)",
             "url": "https://www.nhc.noaa.gov/data/tcr/AL142018_Michael.pdf", "retrieved_at": retrieved},
            {"name": "IEM archived NWS VTEC watch/warning shapefile (WFO TAE, MOB)",
             "url": WWA_URL, "retrieved_at": retrieved},
            {"name": "IEM AFOS archive - Hurricane Local Statements HLSTAE",
             "url": HLS_URL.format(wfo="TAE"), "retrieved_at": retrieved},
            {"name": "IEM AFOS archive - Hurricane Local Statements HLSMOB",
             "url": HLS_URL.format(wfo="MOB"), "retrieved_at": retrieved},
            {"name": "IEM archived NWS products text (non-tropical alert text, per PROD_ID)",
             "url": NWSTEXT_URL.format(pid="<PROD_ID>"), "retrieved_at": retrieved},
            {"name": "IEM archived ASOS observations (KECP, KTLH, KPNS)",
             "url": ASOS_URL, "retrieved_at": retrieved},
        ],
        "build_notes": {"records_dropped": dropped,
                        "region_bbox_lonlat": list(REGION.bounds),
                        "geometry_simplify_deg": 0.004},
        "snapshots": snapshots,
    }


if __name__ == "__main__":
    data = build()
    OUT.write_text(json.dumps(data, separators=(",", ":")))
    print("wrote", OUT, OUT.stat().st_size // 1024, "KB; dropped:", data["build_notes"]["records_dropped"])
