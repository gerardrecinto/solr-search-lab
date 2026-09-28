# Architecture

## Request flow

```
indexer.add_documents() / bulk_index()
      |
      v
Solr core "buildlogs" (standalone mode, single node)
      |
      +-- text_log field type: StandardTokenizer -> WordDelimiterGraphFilter
      |     -> LowerCaseFilter -> ManagedSynonymGraphFilter -> FlattenGraphFilter
      |     (index-time synonym expansion -- see config/setup_schema.py)
      |
client/search.py
      +-- search()                    plain query
      +-- faceted_search()             + facet.field
      +-- iter_all_results_via_cursor_mark()   deep pagination without offset decay
      +-- relevance_search()           edismax + recency boost function
```

## Why standalone mode, not SolrCloud

SolrCloud (multi-node, ZooKeeper-coordinated, collection aliasing for
zero-downtime reindex) is the production-grade answer to most of what
this project demonstrates with standalone-mode workarounds (core swap
instead of collection aliasing, no replica failover). This lab runs
standalone Solr deliberately: a real SolrCloud cluster needs at least a
3-node ZooKeeper ensemble plus multiple Solr nodes, which on this
machine's resource-constrained Docker Desktop VM (7.65GB total, already
shared across four other portfolio projects' stacks) would either fail to
start reliably or starve the other projects' containers. Standalone
mode's core-swap primitive (`indexing/indexer.py::swap_cores`) demonstrates
the same *zero-downtime reindex* concept SolrCloud's aliasing provides,
without needing the cluster — stated as a scoped-down but honest
substitute, not an equivalent claim to SolrCloud replica-level HA (see
`docs/PORTFOLIO_SUMMARY.md`'s "does NOT support" section).

## Index-time vs. query-time synonyms

Covered in depth in `config/setup_schema.py`'s module docstring. Short
version: index-time synonym expansion (this project's choice) means
simpler, faster queries at the cost of needing to reindex existing
documents when the synonym list changes — verified directly in
`tests/test_synonyms.py::test_pre_existing_doc_does_not_match_new_synonym_until_reindexed`,
not asserted as a hypothetical tradeoff.

## Reindex without downtime, in standalone mode

`indexing/indexer.py::reindex_via_core_swap` builds a complete new index
in a staging core, then calls Solr's `CoreAdmin SWAP` action, which
atomically exchanges which core name points at which underlying index.
Readers querying the live core name see the old data right up until the
swap and the new data immediately after — verified in
`tests/test_reindex.py`, which asserts the live core has zero documents
before the swap and the full new document set immediately after.
