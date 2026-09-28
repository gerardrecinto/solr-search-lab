import uuid
from datetime import datetime, timedelta, timezone

from solr_search_lab.client.search import relevance_search
from tests.helpers import random_tag


def test_recency_boost_ranks_newer_equal_scoring_doc_first(client):
    tag = random_tag()
    now = datetime.now(timezone.utc)

    old_doc_id = str(uuid.uuid4())
    new_doc_id = str(uuid.uuid4())
    client.add(
        [
            {
                "id": old_doc_id,
                "message": f"relevance test {tag}",
                "occurred_at": (now - timedelta(days=300)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            {
                "id": new_doc_id,
                "message": f"relevance test {tag}",
                "occurred_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        ]
    )

    without_boost = relevance_search(client, f"message:{tag}", boost_recent=False)
    with_boost = relevance_search(client, f"message:{tag}", boost_recent=True)

    without_boost_ids = [doc["id"] for doc in without_boost]
    with_boost_ids = [doc["id"] for doc in with_boost]

    assert set(without_boost_ids) == {old_doc_id, new_doc_id}
    assert with_boost_ids[0] == new_doc_id
