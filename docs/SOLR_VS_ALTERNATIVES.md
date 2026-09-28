# When Solr, when Postgres full-text search, when OpenSearch

## Where this project's use case fits Solr

- Rich, tunable text analysis per field (the `text_log` field type's full
  index-time analyzer chain — tokenization, word-delimiter splitting,
  synonym expansion) is more explicit and composable in Solr's Schema API
  than Postgres's `tsvector`/`tsquery`, which uses a fixed dictionary-based
  configuration (`english`, `simple`, etc.) with far less per-field
  customization.
- Faceting (`facet.field`) and cursorMark pagination are first-class,
  well-optimized Solr features this project relies on directly.
- Managed synonym updates via a REST API (no file redeploy) fit an
  operational workflow where the synonym list changes independently of
  code deploys.

## When Postgres full-text search would be the better choice

- **The data already lives in Postgres for other reasons** (this
  portfolio's own `signal-harbor` project, or `kafka-ops-lab`'s
  `deploy_events` table). Adding `tsvector` + a GIN index to an existing
  table avoids running and operating a second system entirely, for search
  needs that don't require Solr's depth (a "search my own app's records"
  feature, not a dedicated log-search product).
- **Search needs are secondary to transactional correctness.** Postgres
  keeps full-text indexes transactionally consistent with the row data by
  construction; Solr's index is a separate system that must be kept in
  sync (via `commitWithin`, a CDC pipeline, or a batch reindex job) —
  extra operational surface this project's own dual-write pattern in the
  sibling `cassandra-ops-lab` project shows the real cost of.
- **Scale is moderate.** A few million rows with straightforward text
  search fits comfortably in Postgres with proper indexing; standing up
  Solr adds real operational cost (see `docs/COST_NOTES.md`) that isn't
  justified until search becomes a first-class, high-volume workload.

## When OpenSearch would be the better choice

- **Multi-node scale-out is a real, near-term requirement**, not a
  someday concern. OpenSearch's distributed model (sharding, replicas) is
  more actively developed and more commonly the default choice for new
  greenfield search infrastructure today than standalone Solr or even
  SolrCloud.
- **The team already runs an ELK/OpenSearch stack for logs/observability.**
  Reusing that same cluster for search avoids operating two separate
  search systems for two different purposes (raw log aggregation vs.
  structured search) when one could reasonably serve both.
- **Built-in vector/hybrid search matters.** OpenSearch's native
  approximate-nearest-neighbor support is more mature out of the box than
  Solr's dense-vector support for combining lexical and semantic search.
- **Solr's specific strengths matter less than ecosystem/hiring fit.**
  If a team already has deep OpenSearch/Elasticsearch operational
  experience and no existing Solr investment, that operational fit is
  often the deciding factor over a feature-by-feature comparison.

## The honest summary

This project chose Solr because the assignment was explicitly to build
Solr hands-on experience — not because Solr strictly outperforms Postgres
FTS or OpenSearch for every log-search workload. In an unconstrained
real-world decision with no existing Solr investment, OpenSearch is
arguably the more common default today for new log/search infrastructure;
Postgres FTS remains the right call whenever the data already lives there
and scale doesn't demand a dedicated search system.
