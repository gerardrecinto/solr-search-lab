# Security notes

## What's implemented

- Field types are strongly typed via the Schema API (`string`, `pdate`,
  custom `text_log`) — malformed field values are rejected by Solr at
  index time, not silently coerced.

## Known limitations (stated, not hidden)

- **No authentication.** This lab's Solr instance has no
  authentication/authorization plugin configured — the admin UI, Schema
  API, and CoreAdmin API (which can create/delete/swap cores) are all
  open to anyone reaching port 8983. Production Solr needs
  `BasicAuthPlugin` or a real identity-backed auth plugin at minimum, plus
  a `RuleBasedAuthorizationPlugin` scoping who can call admin actions like
  `CREATE`/`UNLOAD`/`SWAP` vs. who can only query.
- **CoreAdmin actions are destructive and unauthenticated here.** This
  project's own `unload_core()` helper (used in test cleanup) calls
  `UNLOAD` with `deleteInstanceDir=true` — a real permanent data-deleting
  action. In this lab it's scoped to test-only core names by convention,
  not by any access control; production needs actual authorization
  boundaries around who can invoke this.
- **No encryption in transit.** Plain HTTP on port 8983, no TLS
  configured — a local-lab-only setup.
- **Query injection surface**: this project builds queries as
  `f"message:{tag}"` string interpolation in a few places
  (`scripts/query_performance.py`, some tests) for simplicity. A
  production query builder taking user input must escape Solr's special
  query syntax characters or use `edismax`'s `q.op`/parameter-based
  queries rather than string-interpolating raw user input into a `q`
  parameter, to avoid Solr query-syntax injection.
