# Runbooks

## Symptom: newly added synonym doesn't seem to work

See README's "Real incident #1." Check whether the core was reloaded
after the `PUT` to the Managed Resource endpoint —
`config/setup_schema.py::reload_core()` does this automatically when
called via `setup()`, but a manual `requests.put(...)` bypassing that
helper needs an explicit `RELOAD` afterward.

## Symptom: a document doesn't match a synonym that clearly applies to its text

Check whether the document was indexed **before** the synonym mapping was
added. Index-time synonym expansion (this project's design, see
`docs/ARCHITECTURE.md`) bakes the expansion into the stored tokens at
index time — a synonym added afterward has no retroactive effect on
already-indexed documents. Fix: reindex the affected documents (re-`add()`
them; Solr's `id`-keyed upsert semantics mean re-adding with the same `id`
replaces the old stored tokens). For a full synonym-list change affecting
many documents, `indexing/indexer.py::reindex_via_core_swap` is the
zero-downtime way to rebuild the whole index rather than re-adding
documents in place one at a time.

## Symptom: deep pagination (`start=10000`+) is slow

Expected and measured directly (see README's "Query performance:
observed" table) — `start=N` cost grows with N. Switch to
`client/search.py::iter_all_results_via_cursor_mark` for any "walk the
whole result set" use case (exports, batch reprocessing). cursorMark
cannot jump to an arbitrary page number, only walk forward sequentially
from `*` — it is not a drop-in replacement for a paginated UI that lets a
user jump to page 47 directly; that UI pattern needs `start=N` and should
bound how deep a user is allowed to page (e.g., cap at 1,000 results, push
them toward filtering instead).

## Failure recovery (standalone mode's real limitation)

This lab runs standalone Solr, not SolrCloud — there is no replica to
fail over to. The only failure-recovery property actually verified here
is restart durability: stop the container (`docker compose stop`), start
it again (`docker compose up -d`), and confirm previously indexed
documents are still present (Solr's transaction log + hard commits on
the persisted `solr_data` volume handle this). Full node-failure/replica
failover testing, as done for real in the sibling `cassandra-ops-lab`
project's 3-node cluster, would require standing up SolrCloud with
multiple nodes and ZooKeeper — not built here, stated as a scope
limitation (`docs/ARCHITECTURE.md`'s "Why standalone mode" section), not
implied to exist.

## Reindexing strategy for a synonym-list or schema change

1. Update the synonym list or field type in a staging core
   (`indexing/indexer.py::create_core` + the same `setup_schema_fn`).
2. Bulk-index the current data into the staging core.
3. `swap_cores(live_core, staging_core)` — atomic, zero read-downtime.
4. Unload the now-retired old core once confident in the new one.
