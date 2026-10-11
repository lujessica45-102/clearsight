import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
_tmp = tempfile.mkdtemp(prefix="cs_backend_")
# Tests never touch the developer's cache, decision log or facility database.
os.environ.setdefault("CLEARSIGHT_CACHE_DIR", os.path.join(_tmp, "cache"))
os.environ.setdefault("CLEARSIGHT_DATA_DIR", _tmp)
os.environ.setdefault("FACILITIES_DATABASE", os.path.join(_tmp, "facilities.db"))
for k in ("OBJ_ENDPOINT", "OBJ_BUCKET", "OBJ_ACCESS_KEY", "OBJ_SECRET_KEY", "CLEARSIGHT_NOW"):
    os.environ.pop(k, None)


def pytest_configure(config):
    config.addinivalue_line("markers", "network: queries real NWS/IEM/Census services; skipped automatically if unreachable")


@pytest.fixture(scope="session")
def services_up():
    import requests
    for url in ("https://mesonet.agron.iastate.edu/api/1/vtec/events_status.json", "https://api.weather.gov/"):
        try:
            requests.get(url, params={"valid": "2018-10-10T09:00:00Z", "wfo": "TAE"} if "mesonet" in url else None,
                         headers={"User-Agent": "ClearSight-tests"}, timeout=15).raise_for_status()
        except Exception as e:
            pytest.skip(f"{url} unreachable: {e}")


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    import evidence_api
    return TestClient(evidence_api.app)
