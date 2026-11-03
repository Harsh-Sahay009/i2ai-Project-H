## Why

Reproducibility (error e) and D5's "rerun from the report alone" need every input and output of a run stored immutably and traceable. The atlas says an episode becomes experience only when it is versioned to the exact model, prompts, rules, thresholds and domain that produced it.

## What Changes

- Add a content-addressed store (CAS) for data artifacts with immutable writes.
- Add a lineage index (DuckDB) linking artifacts to parents and to run ids.
- Add registration of Git-tagged artifacts (taxonomy, prompts, lexicon, metric definitions, price table) by tag and commit.
- Add `itemizer rerun <run_id>` restoration support.

## Capabilities

### New Capabilities
- `version-registry`: immutable storage, identification, lineage and restoration of every versioned artifact listed in `architecture/docs/05-data-versioning.md`.

### Modified Capabilities
<!-- none -->

## Impact

- New package `itemizer.registry`; data under `${runtime.data_root}/cas` and `${runtime.data_root}/registry.duckdb`, ignored by Git.
- Used by every container that reads or writes data.
- Depends on `add-common-core-contracts`.
