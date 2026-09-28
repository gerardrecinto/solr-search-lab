# Cost notes

Everything runs in a local Docker container — no managed search service
(a hosted Solr offering, or OpenSearch/Elasticsearch service) was
provisioned, so no cloud cost was incurred.

## Design decisions that would matter for cost at production scale

- **Standalone mode vs. SolrCloud**: standalone is cheaper to run (one
  node, no ZooKeeper ensemble) but has no horizontal scale-out or replica
  redundancy — the right choice only while data volume and availability
  requirements are modest. See `docs/ARCHITECTURE.md` for why this lab
  uses it (resource constraints on this specific machine, not a
  production recommendation).
- **Index-time synonym expansion** costs slightly more index-time CPU and
  slightly larger index size (more tokens stored per document) in
  exchange for cheaper, simpler queries — the right tradeoff for a
  read-heavy search workload, which log/build search typically is
  (indexed rarely relative to how often it's searched).
- **`commitWithin` (near-real-time) instead of aggressive hard commits**:
  batches document visibility rather than committing after every single
  add, reducing I/O and CPU cost of frequent hard commits at the cost of
  a bounded visibility delay (this project defaults to 1000ms).

## What's not modeled

No production-scale sizing (shard count, replica count, node instance
sizing) or managed-service pricing comparison — this project demonstrates
schema design and query mechanics; sizing a real deployment depends on
actual document volume and query rate this lab doesn't have.
