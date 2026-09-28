import pysolr
import pytest
import requests

from solr_search_lab.config.setup_schema import setup

CORE = "buildlogs"
SOLR_BASE = "http://localhost:8983/solr"


@pytest.fixture(scope="session", autouse=True)
def ensure_schema():
    try:
        requests.get(f"{SOLR_BASE}/admin/cores", params={"action": "STATUS"}, timeout=5).raise_for_status()
    except requests.exceptions.ConnectionError:
        pytest.skip(f"local Solr not reachable at {SOLR_BASE} (docker compose up -d)")
    setup(CORE)


@pytest.fixture
def client():
    return pysolr.Solr(f"{SOLR_BASE}/{CORE}", always_commit=True, timeout=10)
