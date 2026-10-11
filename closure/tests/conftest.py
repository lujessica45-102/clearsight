import os
import tempfile

import pytest

# Tests never share the developer's cache or decision log.
os.environ.setdefault("CLEARSIGHT_CACHE_DIR", tempfile.mkdtemp(prefix="cs_cache_"))


def pytest_configure(config):
    config.addinivalue_line("markers", "network: queries real NWS/IEM services; skipped automatically if they are unreachable")


@pytest.fixture(scope="session")
def iem_up():
    import requests
    try:
        requests.get("https://mesonet.agron.iastate.edu/api/1/vtec/events_status.json", params={"valid": "2018-10-10T09:00:00Z", "wfo": "TAE"}, timeout=15).raise_for_status()
    except Exception as e:
        pytest.skip(f"IEM unreachable: {e}")


@pytest.fixture(scope="session")
def nws_up():
    import requests
    try:
        requests.get("https://api.weather.gov/", headers={"User-Agent": "ClearSight-tests"}, timeout=15).raise_for_status()
    except Exception as e:
        pytest.skip(f"NWS unreachable: {e}")
