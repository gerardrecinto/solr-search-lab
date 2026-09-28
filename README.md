# solr-search-lab

A Solr search portfolio project: schema and text-analysis design for
searching CI build logs, synonym expansion, faceting, cursorMark
pagination, relevance tuning, and a zero-downtime reindex via core swap —
run against a real local Solr instance, with three real operational
gotchas hit and fixed while building it.

**Honesty note**: this closes a genuine hands-on gap. Everything here,
including the three incidents below, was hit and fixed in this lab, not
written from documentation alone.

## Local quickstart

```bash
docker compose up -d
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

python -m solr_search_lab.config.setup_schema   # field type, fields, synonyms, core reload
python -m pytest tests/ -v
python scripts/query_performance.py
```

**Observed**: 6/6 tests passing against a real local Solr 9 instance.

## Real incident #1: Managed synonym updates need a core reload

Adding a synonym via the Managed Resource REST API
(`PUT /solr/buildlogs/schema/analysis/synonyms/devops_errors`) updates the
on-disk synonym map immediately but does **not** affect the already-running
core's analyzer chain — verified directly: analyzing `"OutOfMemoryError"`
showed no `oom` token until `python -m solr_search_lab.config.setup_schema`
issued a `RELOAD` core-admin action. `config/setup_schema.py::setup()`
always reloads after loading synonyms for exactly this reason.

## Real incident #2: dynamic core creation needs a registered configset

`solr-precreate buildlogs` (this repo's docker-compose command) copies the
`_default` configset straight into the `buildlogs` core's own instance
directory — it does not register `_default` under the shared
`$SOLR_HOME/configsets/` path that `CoreAdmin`'s `CREATE` action's
`configSet` parameter looks up. The first attempt at
`indexing/indexer.py::create_core()` failed with:

```
Could not load configuration from directory /var/solr/data/configsets/_default
```

Fixed with a one-time, idempotent copy from the running core's own
`conf/` into the shared location (`indexer.py::_ensure_default_configset_registered`).

## Real incident #3: pysolr's `Results` object auto-paginates on iteration

`iter_all_results_via_cursor_mark()` originally called `list(results)`
inside its own manual cursorMark loop — but pysolr's `Results.__iter__`
already walks the *entire* remaining cursorMark sequence internally when
iterated directly. The result: a 137-document test returned 539 documents
(pysolr's internal auto-pagination and this function's own loop both
paging, overlapping). Fixed by reading `results.docs` (the single page)
instead of iterating `results` itself — see the docstring in
`client/search.py` for the full explanation, and
`tests/test_pagination.py` for the regression test that caught it.

## Query performance: observed (8,000 synthetic log lines, single local node)

```
== deep pagination: start=N vs cursorMark at equivalent depth ==
  start=   10: QTime=6ms
  start= 1000: QTime=20ms
  start= 5000: QTime=30ms

== plain query vs faceted query ==
  plain:   QTime=1ms
  faceted: QTime=3ms
```

`start=N` degrades with depth because Solr has to walk and discard the
first N matches internally on every request — at 5,000 it's already 5x
the cost of a shallow page, on only 8,000 total documents. `cursorMark`
avoids this by resuming directly from the last sort value seen, not a
numeric offset (see `client/search.py::iter_all_results_via_cursor_mark`'s
docstring) — the tradeoff is that cursorMark can't jump to an arbitrary
page N, only walk forward sequentially, which is the right tool for
"export everything" or "keep scrolling," not "show me page 47."

## Text analysis: what actually happens to a log line

`OutOfMemoryError detected` analyzes (index-time) to:

```
StandardTokenizer        -> OutOfMemoryError, detected
WordDelimiterGraphFilter -> OutOfMemoryError, Out, Of, Memory, Error, detected
LowerCaseFilter          -> outofmemoryerror, out, of, memory, error, detected
SynonymGraphFilter       -> oom, out, outofmemoryerror, of, memory, ..., detected
FlattenGraphFilter       -> (graph flattened for indexing)
```

Verified directly via Solr's `/analysis/field` endpoint, not asserted —
see `config/setup_schema.py`'s module docstring for why each filter is in
this specific order (particularly why `FlattenGraphFilter` must come
last, and why synonyms are expanded at index time rather than query time).

## Repo layout

```
solr_search_lab/
  config/setup_schema.py    field type + fields + managed synonyms, schema-as-code
  log_generator.py            synthetic CI log line generator
  indexing/indexer.py         NRT adds (commitWithin) + zero-downtime reindex via core swap
  client/search.py            plain search, faceting, cursorMark pagination, edismax relevance boost
  monitoring.py                ping, core status, real server-side QTime
docker-compose.yml             single-node Solr 9 (standalone, not SolrCloud -- see docs/ARCHITECTURE.md)
scripts/query_performance.py   real QTime measurements, deep pagination and faceting
tests/                          6 tests, real integration against live Solr, incl. 2 regression tests for real bugs hit
docs/                            architecture, runbooks (3 real incidents), Solr-vs-Postgres-vs-OpenSearch,
                                 security, cost, troubleshooting, portfolio summary
```
