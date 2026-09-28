# Troubleshooting

## Synonym doesn't seem to apply after adding it

See README's "Real incident #1" — reload the core
(`config/setup_schema.py::reload_core`) after any Managed Resource
(synonym) update. `setup()` does this automatically.

## `Could not load configuration from directory /var/solr/data/configsets/_default`

See README's "Real incident #2" — `indexing/indexer.py::create_core()`
now calls `_ensure_default_configset_registered()` automatically, which
copies the running `buildlogs` core's own `conf/` into the shared
configsets location the first time it's needed. This requires the
`docker` CLI to be able to `exec` into the container named
`solr-search-lab-solr-1` (the name this repo's `docker-compose.yml`
produces) — if you renamed the service, update `SOLR_CONTAINER_NAME` in
`indexer.py`.

## A cursorMark-based pagination helper returns more documents than expected

See README's "Real incident #3" — check whether you're calling
`list(results)` or `for doc in results` directly on a pysolr `Results`
object with a `cursorMark` param, which triggers pysolr's own hidden
auto-pagination. Use `results.docs` for a single page.

## Tests skip or connection errors

Confirm Solr is actually up: `curl http://localhost:8983/solr/admin/cores?action=STATUS`.
The `ensure_schema` fixture in `tests/conftest.py` calls `pytest.skip(...)`
if it can't reach Solr at all, but a core that exists with a broken
schema will surface as real test failures, not a skip — re-run
`python -m solr_search_lab.config.setup_schema` if schema-related tests
fail unexpectedly.

## Leftover test cores accumulating

`tests/test_reindex.py` creates and unloads its own throwaway cores
(`test-reindex-live-*`, `test-reindex-staging-*`) per run, with cleanup in
a `finally` block — if a test run is killed mid-test (not a normal
failure), a stray core can be left behind. List them with
`curl http://localhost:8983/solr/admin/cores?action=STATUS` and unload
manually with `action=UNLOAD&core=<name>&deleteInstanceDir=true`.
