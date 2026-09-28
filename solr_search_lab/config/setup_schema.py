"""Schema-as-code via Solr's Schema API and Managed Resource API -- no
hand-edited managed-schema XML or custom configset baked into the image.
Run:

    python -m solr_search_lab.config.setup_schema

**Analysis chain design** (the `text_log` field type):

Index analyzer: StandardTokenizer -> WordDelimiterGraphFilter (splits
`OutOfMemoryError` into `Out`/`Of`/`Memory`/`Error` AND keeps the
concatenated form, via `catenateWords`) -> LowerCaseFilter ->
ManagedSynonymGraphFilter (expands DevOps shorthand -- "oom" indexes as
"oom outofmemoryerror") -> FlattenGraphFilter (required whenever a graph
filter like WordDelimiterGraphFilter or SynonymGraphFilter appears before
indexing -- Lucene's index format can't store a token graph directly).

Query analyzer: StandardTokenizer -> WordDelimiterGraphFilter ->
LowerCaseFilter. No synonym filter at query time.

**Why index-time synonyms, not query-time**: expanding synonyms into the
index means a search for "oom" matches a doc that only ever said
"OutOfMemoryError", using a plain term match at query time -- simpler,
faster queries, no synonym-driven query expansion cost. The real cost:
changing the synonym list only affects documents indexed AFTER the
change. An existing document indexed before "oom" was mapped to
"outofmemoryerror" will NOT retroactively match a search for "oom" until
it's reindexed. This is why `indexing/reindex.py` exists and why
`docs/RUNBOOKS.md` documents the reindex-on-synonym-change procedure --
not a hypothetical concern, verified in
`tests/test_synonyms.py::test_pre_existing_doc_does_not_match_new_synonym_until_reindexed`.
"""

import requests

SOLR_BASE = "http://localhost:8983/solr"
CORE = "buildlogs"
SYNONYM_DICTIONARY = "devops_errors"

FIELD_TYPE_PAYLOAD = {
    "add-field-type": {
        "name": "text_log",
        "class": "solr.TextField",
        "indexAnalyzer": {
            "tokenizer": {"class": "solr.StandardTokenizerFactory"},
            "filters": [
                {
                    "class": "solr.WordDelimiterGraphFilterFactory",
                    "generateWordParts": 1,
                    "generateNumberParts": 1,
                    "catenateWords": 1,
                    "catenateNumbers": 0,
                    "catenateAll": 0,
                    "splitOnCaseChange": 1,
                },
                {"class": "solr.LowerCaseFilterFactory"},
                {"class": "solr.ManagedSynonymGraphFilterFactory", "managed": SYNONYM_DICTIONARY},
                {"class": "solr.FlattenGraphFilterFactory"},
            ],
        },
        "queryAnalyzer": {
            "tokenizer": {"class": "solr.StandardTokenizerFactory"},
            "filters": [
                {
                    "class": "solr.WordDelimiterGraphFilterFactory",
                    "generateWordParts": 1,
                    "generateNumberParts": 1,
                    "catenateWords": 1,
                    "catenateNumbers": 0,
                    "catenateAll": 0,
                    "splitOnCaseChange": 1,
                },
                {"class": "solr.LowerCaseFilterFactory"},
            ],
        },
    }
}

FIELDS_PAYLOAD = {
    "add-field": [
        {"name": "build_id", "type": "string", "stored": True, "indexed": True, "docValues": True},
        {"name": "service", "type": "string", "stored": True, "indexed": True, "docValues": True},
        {"name": "environment", "type": "string", "stored": True, "indexed": True, "docValues": True},
        {"name": "log_level", "type": "string", "stored": True, "indexed": True, "docValues": True},
        {"name": "message", "type": "text_log", "stored": True, "indexed": True},
        {"name": "raw_line", "type": "string", "stored": True, "indexed": False},
        {"name": "occurred_at", "type": "pdate", "stored": True, "indexed": True, "docValues": True},
    ]
}

# Curated DevOps error shorthand -> canonical term(s). Multi-way mappings
# so any listed term matches any other in the same group.
SYNONYM_GROUPS = [
    ["oom", "outofmemoryerror", "out of memory"],
    ["econnrefused", "connection refused"],
    ["nospaceleft", "disk full", "no space left on device"],
    ["etimedout", "connection timed out", "timeout"],
    ["npe", "nullpointerexception", "null pointer exception"],
]


def create_field_type_and_fields(core: str = CORE) -> None:
    schema_url = f"{SOLR_BASE}/{core}/schema"
    response = requests.post(schema_url, json=FIELD_TYPE_PAYLOAD, timeout=10)
    if response.status_code != 200 and "already exists" not in response.text:
        response.raise_for_status()

    response = requests.post(schema_url, json=FIELDS_PAYLOAD, timeout=10)
    if response.status_code != 200 and "already exists" not in response.text:
        response.raise_for_status()


def load_synonyms(core: str = CORE, dictionary: str = SYNONYM_DICTIONARY) -> None:
    url = f"{SOLR_BASE}/{core}/schema/analysis/synonyms/{dictionary}"
    for group in SYNONYM_GROUPS:
        response = requests.put(url, json=group, timeout=10)
        response.raise_for_status()


def reload_core(core: str = CORE) -> None:
    """Managed Resource (synonym) updates land in the on-disk synonym map
    immediately, but the already-instantiated analyzer chain in the running
    core does NOT pick them up until the core reloads -- verified directly:
    a synonym added via load_synonyms() had no effect on analysis output
    until this reload ran. See docs/TROUBLESHOOTING.md."""
    response = requests.get(f"{SOLR_BASE}/admin/cores", params={"action": "RELOAD", "core": core}, timeout=15)
    response.raise_for_status()


def setup(core: str = CORE) -> None:
    create_field_type_and_fields(core)
    load_synonyms(core)
    reload_core(core)


if __name__ == "__main__":
    setup()
    print(f"schema and synonyms configured for core '{CORE}'")
