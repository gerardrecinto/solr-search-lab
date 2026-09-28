import uuid
from datetime import datetime, timedelta, timezone

from solr_search_lab.client.search import iter_all_results_via_cursor_mark
from tests.helpers import random_tag


def test_cursor_mark_returns_every_document_exactly_once(client):
    tag = random_tag()
    base_time = datetime.now(timezone.utc)
    docs = [
        {
            "id": str(uuid.uuid4()),
            "message": f"pagination test {tag}",
            "occurred_at": (base_time + timedelta(seconds=i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        for i in range(137)  # deliberately not a round multiple of page_size
    ]
    client.add(docs)

    seen_ids = [doc["id"] for doc in iter_all_results_via_cursor_mark(client, f"message:{tag}", page_size=20)]

    assert len(seen_ids) == 137
    assert len(set(seen_ids)) == 137  # no duplicates across page boundaries
