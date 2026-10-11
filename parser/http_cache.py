"""Small on-disk cache for the HTTP responses the as-of data layer fetches (NWS recent history, IEM archive).

Every result carries `cached` and the ORIGINAL retrieval time, so the UI can say "cached copy of a real response
retrieved <time>". Nothing here is a fixture: entries are created only by real requests made at query time.

  CLEARSIGHT_CACHE_DIR   cache location (default ~/.clearsight/cache; deliberately NOT under ~/Desktop, where iCloud
                         sync caused SQLite/file I/O errors)
  CLEARSIGHT_OFFLINE=1   serve the cache only; a miss raises OfflineCacheMiss instead of touching the network
"""
import gzip
import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

DEFAULT_TIMEOUT = 40


class OfflineCacheMiss(RuntimeError):
    """CLEARSIGHT_OFFLINE=1 and the requested response is not in the cache."""


def cache_dir():
    d = Path(os.getenv("CLEARSIGHT_CACHE_DIR") or Path.home() / ".clearsight" / "cache")
    d.mkdir(parents=True, exist_ok=True)
    return d


def offline():
    return os.getenv("CLEARSIGHT_OFFLINE", "").strip().lower() in ("1", "true", "yes")


def user_agent():
    return os.getenv("NWS_USER_AGENT", "ClearSight-USDA-hackathon (contact: set NWS_USER_AGENT)")


def _key(url, params):
    raw = url + "?" + json.dumps(params or {}, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def _path(key):
    return cache_dir() / key[:2] / f"{key}.json.gz"


def _read(key):
    p = _path(key)
    if not p.exists():
        return None
    try:
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None  # corrupt entry: treat as a miss


def _write(key, entry):
    p = _path(key)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    os.close(fd)
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(entry, f)
    os.replace(tmp, p)


def cached_get_json(url, params=None, ttl_seconds=None, headers=None, retries=3, timeout=DEFAULT_TIMEOUT):
    """GET url -> (json, meta). ttl_seconds=None means the entry never expires (archive data).

    meta = {"url", "cached": bool, "retrieved_at": ISO of the ORIGINAL fetch, "stale": bool}
    """
    key = _key(url, params)
    entry = _read(key)
    now = time.time()
    fresh = entry is not None and (ttl_seconds is None or now - entry["fetched_epoch"] <= ttl_seconds)
    if fresh:
        return entry["data"], {"url": url, "cached": True, "retrieved_at": entry["retrieved_at"], "stale": False}
    if offline():
        if entry is not None:  # offline: an expired entry is still better than nothing, and is labelled stale
            return entry["data"], {"url": url, "cached": True, "retrieved_at": entry["retrieved_at"], "stale": True}
        raise OfflineCacheMiss(f"CLEARSIGHT_OFFLINE is set and no cached response exists for {url} {params or ''}")

    hdrs = {"User-Agent": user_agent(), "Accept": "application/json"}
    hdrs.update(headers or {})
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=hdrs, timeout=timeout)
            if r.status_code >= 500 or r.status_code == 429:
                raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
            r.raise_for_status()
            data = r.json()
            retrieved = datetime.now(timezone.utc).isoformat()
            _write(key, {"url": url, "params": params, "retrieved_at": retrieved, "fetched_epoch": now, "data": data})
            return data, {"url": url, "cached": False, "retrieved_at": retrieved, "stale": False}
        except Exception as e:  # network error / bad JSON / 5xx: retry with backoff, then fall back to any stale entry
            last = e
            if isinstance(e, requests.HTTPError) and e.response is not None and e.response.status_code < 500 and e.response.status_code != 429:
                break
            time.sleep(0.6 * (attempt + 1))
    if entry is not None:
        return entry["data"], {"url": url, "cached": True, "retrieved_at": entry["retrieved_at"], "stale": True}
    raise last
