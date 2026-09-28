"""Real QTime measurements: deep offset pagination (start=N) vs cursorMark
at equivalent depth, and a plain vs faceted query. Run:

    python scripts/query_performance.py
"""

import random
import time

import pysolr

from solr_search_lab.config.setup_schema import setup
from solr_search_lab.log_generator import generate_log_line
from solr_search_lab.monitoring import query_time_ms

CORE = "buildlogs"
SOLR_BASE = "http://localhost:8983/solr"


def bulk_index(n_docs: int) -> None:
    client = pysolr.Solr(f"{SOLR_BASE}/{CORE}", always_commit=False, timeout=30)
    rng = random.Random(99)
    batch = [generate_log_line(rng) for _ in range(n_docs)]
    for i in range(0, len(batch), 500):
        client.add(batch[i : i + 500], commitWithin=2000)
    client.commit()


def main() -> None:
    setup(CORE)

    print("== indexing 8000 synthetic log lines for a meaningful deep-pagination test ==")
    bulk_index(8000)

    print("\n== deep pagination: start=N vs cursorMark at equivalent depth ==")
    for depth in (10, 1000, 5000):
        start_qtime = query_time_ms(CORE, "*:*", start=depth, rows=10, sort="id asc")
        print(f"  start={depth:5d}: QTime={start_qtime}ms")

    print("\n== plain query vs faceted query ==")
    plain_qtime = query_time_ms(CORE, "log_level:ERROR")
    faceted_qtime = query_time_ms(
        CORE, "log_level:ERROR", **{"facet": "true", "facet.field": ["service", "environment"]}
    )
    print(f"  plain:   QTime={plain_qtime}ms")
    print(f"  faceted: QTime={faceted_qtime}ms")


if __name__ == "__main__":
    main()
