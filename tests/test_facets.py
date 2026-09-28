import uuid

from solr_search_lab.client.search import faceted_search
from tests.helpers import random_tag


def test_facet_counts_match_indexed_distribution(client):
    tag = random_tag()
    docs = [
        {"id": str(uuid.uuid4()), "message": f"facet test {tag}", "log_level": "ERROR"},
        {"id": str(uuid.uuid4()), "message": f"facet test {tag}", "log_level": "ERROR"},
        {"id": str(uuid.uuid4()), "message": f"facet test {tag}", "log_level": "WARN"},
    ]
    client.add(docs)

    results = faceted_search(client, f"message:{tag}", facet_fields=["log_level"])
    facet_counts = dict(zip(results.facets["facet_fields"]["log_level"][::2], results.facets["facet_fields"]["log_level"][1::2]))

    assert facet_counts["ERROR"] == 2
    assert facet_counts["WARN"] == 1
