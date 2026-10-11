# Hurricane Michael replay fixture (`michael_2018.json`)

**Historical replay of archived real NWS records. Not live data.** Rebuild with
`python build_michael_fixture.py` (build-time deps: requests, pyshp, shapely).

## Why Michael, not Isaias
Isaias was a 2020 storm (late July/early Aug, Atlantic coast) - it cannot be the Oct 9 emergency.
Michael (AL142018) fits: landfall **Wed Oct 10, 2018 ~1730 UTC (12:30 PM CDT)** near Tyndall AFB / Mexico Beach as a
**Category 5, 140 kt, 919 mb** (NHC Tropical Cyclone Report, https://www.nhc.noaa.gov/data/tcr/AL142018_Michael.pdf,
retrieved and read 2026-10-11). Directly hit Panama City; Pensacola and Tallahassee saw lesser impacts.

## Sources (all retrieved 2026-10-11 UTC, no API key)
| What | Exact request |
|---|---|
| Watch/warning geometry + VTEC times (WFO TAE, MOB; Oct 8-12 2018) | `https://mesonet.agron.iastate.edu/cgi-bin/request/gis/watchwarn.py?wfo[]=TAE&wfo[]=MOB&year1=2018&month1=10&day1=8&hour1=0&minute1=0&year2=2018&month2=10&day2=12&hour2=0&minute2=0` (returns a shapefile zip, whatever `format=` is passed) |
| Tropical narrative text (Hurricane Local Statements) | `https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?pil=HLS{TAE,MOB}&sdate=2018-10-08T00:00Z&edate=2018-10-12T00:00Z&fmt=text&limit=100` |
| Non-tropical alert text (Extreme Wind, Flash Flood, Tornado Watch, ...) | `https://mesonet.agron.iastate.edu/api/1/nwstext/<PROD_ID>` |
| Observations KECP (Panama City area), KTLH, KPNS | `https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=ECP&station=TLH&station=PNS&data=sknt&data=gust&data=mslp&data=wxcodes&data=vsby&data=metar&year1=2018&month1=10&day1=9&...&tz=UTC&format=onlycomma&report_type=3&report_type=4` |

## Real vs derived
- **Real, copied as archived:** VTEC phenomena/significance/ETN, zone and polygon geometry, issuance times, HLS and
  product text, ASOS values (raw METAR included).
- **Derived by us:** the five `as_of` snapshots (a time filter: record in effect if `ISSUED <= as_of < EXPIRED`);
  grouping UGC zones into one alert per VTEC event (geometry = union of in-effect zones, or the storm-based polygon
  when one exists); the `event` name (standard VTEC code table); geometry simplified to ~0.004 deg and rounded to 4 dp;
  `max_wind_or_gust_kt_prior_6h` (max of observed wind/gust in the 6 h before `as_of`).
- **Deliberately null:** `severity`/`urgency`/`certainty` (CAP fields are not in the VTEC archive - the app must map
  from `vtec` using a labeled prototype rule), `onset`, and `expires` for tropical events and cancelled/extended
  records (the archive end time is hindsight or an NHC placeholder, so showing it would leak the future).
- **No look-ahead:** each alert's text comes from a product issued at or before `as_of` (checked by the loader test).

## Gaps / limitations
- **No road closures.** There is no archived 511 data here; do not claim any.
- Alert names are UGC codes (e.g. `FLZ108`, `FLC005`), not place names - the archive has none.
- Excluded on purpose: marine zones; `FL.W` river-flood polygons (archive `ISSUED`/`EXPIRED` are internally
  inconsistent); non-life-safety products (small craft, beach hazards, rip currents). Region clip: lon -88..-83,
  lat 29.2..31.2.
- **No Tornado Warnings** appear in the TAE/MOB pull (only Tornado Watch). I did not independently confirm whether
  any were issued that day.
- Oct 11 07:00 CDT snapshot has **zero** in-scope alerts (all tropical alerts were cancelled by ~04:43Z). Residual
  river flooding is not represented.
- KECP stopped reporting pressure at landfall and reported no wind by the next morning (station outage); missing
  values are `null`. KPFN has no archive at all.
- `facts.landfall_utc` is approximate ("near 1730 UTC" per NHC); impact/surge figures are NHC TCR estimates.
- The shapefile reader logged "orphaned interior hole" warnings for a few multipart zones; those rings were kept as
  exteriors, which cannot shrink the covered area.
