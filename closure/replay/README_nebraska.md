# Replay fixture: March 2019 eastern Nebraska flooding (`nebraska_2019.json`)

**HISTORICAL REPLAY, not live data.** Rebuild with `python build_nebraska_fixture.py` (needs requests, pyshp, shapely; the app only reads the JSON).

## Why this event
Verified from NWS pages (retrieved at build time, URLs in the JSON `sources`):
- A rapidly deepening low ("bomb cyclone", 994 -> ~970 mb in 15 h, Mar 12-13) brought heavy rain, warmth and rapid snowmelt onto frozen ground (>2 ft) Mar 12-14 (NWS Hastings; NWS flood-safety page).
- Nearly 50 levees breached on the Platte, Elkhorn and Missouri Rivers; a Platte levee breach forced evacuation of NWS Omaha/Valley; Valley and Fremont were cut off by flooded roads; about one-third of Offutt AFB flooded; I-29 south of Omaha stayed closed (NWS).
- Mar 13 (Wed), 14 (Thu), 15 (Fri) and 18 (Mon) 2019 were weekdays, so operating-day logic applies.

**What it is NOT:** a blizzard for Lincoln/Omaha. Blizzard conditions on Mar 14 were in central Nebraska (GID). I checked the archive: for the facility locations the OAX products are flood-driven (Flood Watch, areal Flood Warnings, Flash Flood Warnings) plus wind products. A Winter Storm Warning, High Wind Warning and Winter Weather Advisory exist in OAX for northern zones that overlap the bounding region but do not cover the Lincoln/Omaha facility points (verified by point-in-geometry; see engine output). A 4 AM "snow day" story would be fabricated.

## Sources (real)
- IEM VTEC archive shapefile, WFO OAX, 2019-03-12 to 03-19: alert type, issue/effective times, storm-based polygons (flood/flash-flood warnings) or UGC zone shapes. https://mesonet.agron.iastate.edu/cgi-bin/request/gis/watchwarn.py
- IEM `nwstext` API: the official text of each product, per PROD_ID.
- IEM ASOS: KLNK and KOMA observations (wind, gust, pressure, weather codes, raw METAR).

## Real vs derived
- Real: alert existence, types, issue times, geometry (simplified to 0.004 deg), text, observations.
- Derived: snapshots are a time filter (`ISSUED <= as_of < EXPIRED`) over archived records. `event` names map from VTEC codes (FA.W -> "Flood Warning", etc.). `geometry_kind` is `polygon` when the archive has a storm-based polygon, else `county_zone`.
- Withheld to avoid hindsight: `expires` is only set when the warning was in its original "NEW" state with no extension yet; otherwise null with `expires_note`.

## Gaps
- No archived road closures / 511 data (none available).
- `severity`, `urgency`, `certainty` are null (not in VTEC archive); the app must map from VTEC.
- River-forecast-point flood products (VTEC phenomena FL, e.g. Elkhorn/Platte river gauges) are excluded, as in the Michael fixture. They exist in the archive and would add river-specific warnings.
- 27 archive records with ISSUED >= EXPIRED were dropped.
- Areal flood warning polygons are broad (all five facility points fall inside); they overstate precise exposure.
