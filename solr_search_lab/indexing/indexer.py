"""Indexing operations: incremental (near-real-time) adds, and a
zero-downtime reindex via Solr's core-swap admin action.
"""

import subprocess
import time

import pysolr
import requests

SOLR_BASE = "http://localhost:8983/solr"
SOLR_CONTAINER_NAME = "solr-search-lab-solr-1"


def _ensure_default_configset_registered(container: str = SOLR_CONTAINER_NAME) -> None:
    """`solr-precreate` (this repo's docker-compose command) creates the
    `buildlogs` core by copying the `_default` configset straight into its
    own instance directory -- it does NOT also register `_default` under
    the shared `$SOLR_HOME/configsets/` directory that CoreAdmin's CREATE
    action's `configSet` parameter looks up. Verified directly: the first
    `create_core()` call in this repo failed with "Could not load
    configuration from directory /var/solr/data/configsets/_default"
    because that directory didn't exist. This one-time, idempotent copy
    (from the already-running `buildlogs` core's own conf/) is the fix,
    not a workaround for a bug in this code -- see docs/TROUBLESHOOTING.md.
    """
    check = subprocess.run(
        ["docker", "exec", container, "test", "-d", "/var/solr/data/configsets/_default"],
        capture_output=True,
    )
    if check.returncode == 0:
        return
    subprocess.run(
        [
            "docker", "exec", container, "bash", "-c",
            "mkdir -p /var/solr/data/configsets && cp -r /var/solr/data/buildlogs/conf /var/solr/data/configsets/_default",
        ],
        check=True,
        capture_output=True,
    )


def get_solr_client(core: str, commit_within_ms: int = 1000) -> pysolr.Solr:
    """commitWithin controls near-real-time visibility: a document is
    guaranteed visible to search within this window without an explicit
    hard commit. It is NOT the same as durability -- a hard commit (or
    Solr's transaction log replay on restart) is what survives a crash;
    commitWithin is purely about search-visibility latency."""
    return pysolr.Solr(f"{SOLR_BASE}/{core}", always_commit=False, timeout=10)


def add_documents(client: pysolr.Solr, docs: list[dict], commit_within_ms: int = 1000) -> None:
    client.add(docs, commitWithin=commit_within_ms)


def create_core(core: str, config_set: str = "_default") -> None:
    _ensure_default_configset_registered()
    response = requests.get(
        f"{SOLR_BASE}/admin/cores",
        params={"action": "CREATE", "name": core, "configSet": config_set},
        timeout=30,
    )
    response.raise_for_status()


def swap_cores(core_a: str, core_b: str) -> None:
    """Atomically swaps which core name serves which underlying index --
    clients querying `core_a` before and after this call never see a gap
    in availability. This is Solr standalone mode's reindex-without-downtime
    primitive; SolrCloud's equivalent is collection aliasing, which needs
    ZooKeeper and isn't used in this lab (see docs/ARCHITECTURE.md for why
    standalone mode was chosen here)."""
    response = requests.get(
        f"{SOLR_BASE}/admin/cores",
        params={"action": "SWAP", "core": core_a, "other": core_b},
        timeout=30,
    )
    response.raise_for_status()


def reindex_via_core_swap(
    live_core: str,
    staging_core: str,
    docs: list[dict],
    setup_schema_fn,
) -> None:
    """Builds a fresh index in `staging_core` (new schema/synonyms/data),
    then atomically swaps it in for `live_core`. Readers querying
    `live_core` see the OLD data right up until the swap, then the NEW
    data immediately after -- no window where the index is empty or
    partially built and visible to readers.
    """
    create_core(staging_core)
    setup_schema_fn(staging_core)

    client = get_solr_client(staging_core, commit_within_ms=1000)
    add_documents(client, docs, commit_within_ms=1000)
    client.commit()
    time.sleep(0.5)

    swap_cores(live_core, staging_core)
