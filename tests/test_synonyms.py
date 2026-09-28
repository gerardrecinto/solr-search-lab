import uuid

from solr_search_lab.config.setup_schema import CORE, reload_core
from tests.helpers import random_tag


def test_oom_matches_document_containing_outofmemoryerror(client):
    doc_id = str(uuid.uuid4())
    client.add([{"id": doc_id, "message": "OutOfMemoryError detected during test run"}])

    results = client.search("message:oom")
    assert any(doc["id"] == doc_id for doc in results)


def test_pre_existing_doc_does_not_match_new_synonym_until_reindexed(client):
    unique_term = random_tag()
    canonical_term = random_tag()

    doc_id = str(uuid.uuid4())
    client.add([{"id": doc_id, "message": f"log line mentioning {canonical_term} explicitly"}])

    before_results = client.search(f"message:{unique_term}")
    assert not any(doc["id"] == doc_id for doc in before_results)

    from solr_search_lab.config.setup_schema import SOLR_BASE
    import requests

    requests.put(
        f"{SOLR_BASE}/{CORE}/schema/analysis/synonyms/devops_errors",
        json=[unique_term, canonical_term],
        timeout=10,
    )
    reload_core(CORE)

    after_reload_no_reindex = client.search(f"message:{unique_term}")
    assert not any(doc["id"] == doc_id for doc in after_reload_no_reindex)

    client.add([{"id": doc_id, "message": f"log line mentioning {canonical_term} explicitly"}])

    after_reindex = client.search(f"message:{unique_term}")
    assert any(doc["id"] == doc_id for doc in after_reindex)
