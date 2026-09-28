import uuid

import pysolr
import requests

from solr_search_lab.config.setup_schema import SOLR_BASE, setup
from solr_search_lab.indexing.indexer import create_core, reindex_via_core_swap
from solr_search_lab.log_generator import generate_log_line
import random


def unload_core(core: str) -> None:
    requests.get(
        f"{SOLR_BASE}/admin/cores",
        params={"action": "UNLOAD", "core": core, "deleteInstanceDir": "true"},
        timeout=15,
    )


def test_reindex_via_core_swap_makes_new_data_live():
    suffix = uuid.uuid4().hex[:8]
    live_core = f"test-reindex-live-{suffix}"
    staging_core = f"test-reindex-staging-{suffix}"

    create_core(live_core)
    setup(live_core)

    rng = random.Random(1)
    docs = [generate_log_line(rng) for _ in range(10)]

    live_client_before = pysolr.Solr(f"{SOLR_BASE}/{live_core}", always_commit=True, timeout=10)
    assert len(live_client_before.search("*:*")) == 0

    try:
        reindex_via_core_swap(live_core, staging_core, docs, setup)

        live_client_after = pysolr.Solr(f"{SOLR_BASE}/{live_core}", always_commit=True, timeout=10)
        results = live_client_after.search("*:*", rows=20)
        assert len(results) == len(docs)
    finally:
        # after SWAP, live_core and staging_core names both still exist,
        # just pointing at each other's original data -- unload both.
        unload_core(live_core)
        unload_core(staging_core)
