"""Health and query-performance introspection using Solr's own admin
endpoints -- no external monitoring stack."""

import requests

SOLR_BASE = "http://localhost:8983/solr"


def ping(core: str) -> dict:
    response = requests.get(f"{SOLR_BASE}/{core}/admin/ping", timeout=10)
    response.raise_for_status()
    return response.json()


def core_status(core: str) -> dict:
    response = requests.get(f"{SOLR_BASE}/admin/cores", params={"action": "STATUS", "core": core}, timeout=10)
    response.raise_for_status()
    return response.json()["status"][core]


def query_time_ms(core: str, query: str, **extra_params) -> float:
    """Real QTime as reported by Solr itself (responseHeader.QTime),
    not a client-side wall-clock measurement -- excludes network/client
    overhead, isolating actual server-side query cost."""
    params = {"q": query, "wt": "json", **extra_params}
    response = requests.get(f"{SOLR_BASE}/{core}/select", params=params, timeout=10)
    response.raise_for_status()
    return response.json()["responseHeader"]["QTime"]
