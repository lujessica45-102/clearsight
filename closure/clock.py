"""The app's notion of "now" (the as-of moment). The OS clock is never touched.

Priority: explicit request (e.g. ?asof=...)  >  CLEARSIGHT_NOW environment variable  >  the real system time.
CLEARSIGHT_NOW freezes the app at one instant (ISO-8601); it only affects this app, so TLS and AWS request signing
keep using the real clock.
"""
import os
from datetime import datetime, timedelta, timezone

from parser import nws_client

EARLIEST = datetime(2005, 1, 1, tzinfo=timezone.utc)   # the IEM VTEC archive starts around 2005
FUTURE_TOLERANCE = nws_client.LIVE_TOLERANCE


class ClockError(ValueError):
    """The requested as-of time cannot be served (unparseable, in the future, or before the archive starts)."""


def parse_as_of(value):
    """ISO-8601 string or datetime -> aware UTC datetime. A value with no timezone is read as UTC."""
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00").replace("z", "+00:00"))
        except ValueError:
            raise ClockError(f"Could not read '{value}' as a date/time. Use ISO-8601, e.g. 2018-10-10T09:00:00Z.")
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def resolve_as_of(requested=None, now=None):
    """-> (as_of: aware UTC datetime, info: {requested, source: 'request'|'env'|'system', real_now, mode})."""
    real_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    env = os.getenv("CLEARSIGHT_NOW", "").strip()
    if requested not in (None, ""):
        as_of, source, raw = parse_as_of(requested), "request", str(requested)
    elif env:
        try:
            as_of = parse_as_of(env)
        except ClockError as e:
            raise ClockError(f"CLEARSIGHT_NOW is set but invalid: {e}")
        source, raw = "env", env
    else:
        as_of, source, raw = real_now, "system", None
    if as_of > real_now + FUTURE_TOLERANCE:
        raise ClockError(f"{as_of.isoformat()} is in the future (real time is {real_now.isoformat()}); no alert data exists for it.")
    if as_of < EARLIEST:
        raise ClockError(f"{as_of.isoformat()} is before the NWS alert archive begins (about 2005); no data exists for it.")
    return as_of, {"requested": raw, "source": source, "real_now": real_now.isoformat(), "as_of": as_of.isoformat(),
                   "mode": nws_client.classify_mode(as_of, real_now)}
