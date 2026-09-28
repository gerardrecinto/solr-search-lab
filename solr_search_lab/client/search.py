"""Search operations: plain query, faceting, cursorMark pagination, and
edismax relevance tuning with a recency boost function.
"""

import pysolr


def search(client: pysolr.Solr, query: str, rows: int = 10, start: int = 0, fq: list[str] | None = None):
    return client.search(query, rows=rows, start=start, fq=fq or [])


def faceted_search(client: pysolr.Solr, query: str, facet_fields: list[str], rows: int = 10):
    return client.search(
        query,
        rows=rows,
        **{
            "facet": "true",
            "facet.field": facet_fields,
            "facet.mincount": 1,
        },
    )


def iter_all_results_via_cursor_mark(client: pysolr.Solr, query: str, page_size: int = 50):
    """cursorMark pagination: each page's response carries the cursor for
    the next page, and the loop ends when the returned cursor stops
    advancing. Unlike `start=N`, this doesn't degrade as N grows -- Solr
    doesn't have to walk and discard N documents internally on each
    request, since the cursor directly resumes from the last sort value
    seen. Requires a sort that includes a unique tiebreaker field (`id`
    here), or pagination isn't well-defined for documents with duplicate
    sort keys.

    Note: pysolr's `Results.__iter__`/`list()` already auto-walks cursorMark
    pages internally when iterated directly -- using `results.docs` (the
    single page only) below is deliberate, so this function's own loop is
    what's doing the paging (the mechanism being demonstrated here), not
    pysolr's built-in one running silently underneath it.
    """
    cursor_mark = "*"
    while True:
        results = client.search(
            query,
            rows=page_size,
            sort="occurred_at asc, id asc",
            cursorMark=cursor_mark,
        )
        docs = results.docs
        yield from docs

        next_cursor = results.nextCursorMark
        if next_cursor == cursor_mark or not docs:
            break
        cursor_mark = next_cursor


def relevance_search(client: pysolr.Solr, query: str, boost_recent: bool = False, rows: int = 10):
    """edismax with message^2 weighted over raw_line-derived relevance is
    implicit here since only `message` is queried -- the explicit tuning
    knob demonstrated is the recency boost function (`bf`), which is
    additive to the base text-match score, not a replacement for it."""
    params = {
        "defType": "edismax",
        "qf": "message^2",
    }
    if boost_recent:
        # recip(ms(NOW,occurred_at),3.16e-11,1,1) is the standard Solr
        # recency-boost idiom: score approaches 1 for very recent
        # documents and decays toward 0 for older ones.
        params["bf"] = "recip(ms(NOW,occurred_at),3.16e-11,1,1)"
    return client.search(query, rows=rows, **params)
