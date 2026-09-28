# Portfolio summary

## What this is

A Solr search portfolio project closing a genuine hands-on gap: text
analysis and schema design for CI build-log search, synonym expansion,
faceting, cursorMark pagination, relevance tuning, and a zero-downtime
reindex pattern — including three real operational bugs hit and fixed
while building it, documented with the actual error text and root cause,
not smoothed over into a clean narrative.

## Resume bullets (accurate language only)

- Designed a Solr text-analysis chain (tokenization, word-delimiter
  splitting, index-time synonym expansion) for searching CI build logs,
  verified token-by-token against Solr's own analysis API.
- Implemented cursorMark-based pagination and measured its performance
  advantage over offset-based pagination directly (deep-page QTime grew
  5x at 5,000 rows vs. a shallow page, on real data).
- Built a zero-downtime reindex mechanism using Solr's core-swap admin
  action, verified with a test asserting zero documents before the swap
  and the full new dataset immediately after.
- Diagnosed and fixed three real Solr/pysolr operational issues during
  development: a managed-synonym reload requirement, a dynamic-core
  configset registration gap, and a client-library auto-pagination bug
  that silently duplicated results.

**Not used, and why**: "operated Solr/SolrCloud in production," "scaled
search to production traffic" — no prior professional Solr experience;
this closes a stated gap through new hands-on work, and this lab runs
standalone Solr, not a production SolrCloud cluster.

## Interview talking points

**"Walk me through your text analysis chain."**
`StandardTokenizer` splits on whitespace/punctuation, `WordDelimiterGraphFilter`
splits camelCase (`OutOfMemoryError` -> `Out`/`Of`/`Memory`/`Error`) while
also keeping the concatenated form, `LowerCaseFilter` normalizes case,
`ManagedSynonymGraphFilter` expands DevOps shorthand ("oom" indexes
alongside "outofmemoryerror"), and `FlattenGraphFilter` is required last
because Lucene's index format can't store a token graph directly — every
stage verified against Solr's `/analysis/field` endpoint, shown verbatim
in the README.

**"What's a real bug you hit building this?"**
Three, documented in the README exactly as encountered. The most
interesting: pysolr's `Results` object auto-paginates internally when you
`list()` or iterate it directly if a `cursorMark` param was used — my own
manual cursorMark loop was ALSO paginating, so a 137-document test query
returned 539 documents from double-pagination. Fixed by reading
`results.docs` instead. Caught by a test I wrote specifically to verify
"no duplicates across page boundaries," which is exactly the kind of test
that catches this class of bug.

**"Why index-time synonyms instead of query-time?"**
Simpler, faster queries — no synonym expansion cost at query time — at
the real cost of needing to reindex when the synonym list changes.
Verified this cost directly, not just described it:
`tests/test_synonyms.py` shows a document indexed before a synonym
mapping existed only starts matching that synonym after it's explicitly
reindexed.

**"When would you use OpenSearch instead of Solr?"**
See `docs/SOLR_VS_ALTERNATIVES.md` — honestly, for new greenfield search
infrastructure without an existing Solr investment, OpenSearch is often
the more common default today. This project used Solr because the goal
was specifically building Solr hands-on depth, not because Solr strictly
beats OpenSearch here.

## Claims this project supports

- Hands-on Solr schema/text-analysis design, verified token-by-token
  against the live analysis API
- Working faceting, cursorMark pagination, and edismax relevance tuning
  with a recency boost function
- A real zero-downtime reindex mechanism (core swap), tested
- Real observed query-performance numbers showing offset-pagination
  degradation
- Three real, diagnosed-and-fixed operational bugs, each with a
  regression test

## Claims this project does NOT support

- Prior professional Solr/SolrCloud production experience
- Multi-node SolrCloud, ZooKeeper coordination, or replica failover
  (standalone mode only — stated directly in `docs/ARCHITECTURE.md`)
- Production-scale sizing or a managed-service cost comparison
