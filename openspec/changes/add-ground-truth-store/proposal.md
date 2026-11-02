## Why

Accuracy, AUC and every error metric need gold labels, and every prediction needs a category list to be judged against. D1 (charge category list, 12–20 categories, client-approved) and D2 (locked test set, 200 distinct notes, blind double-labelled, never used to tune) are deliverables in their own right. If test notes leak into tuning, the reported accuracy is meaningless.

## What Changes

- Add a versioned charge taxonomy with definitions, real examples, catch-all category and client approval record.
- Add evaluation sets TEST (sealed), DEV, FRESH, each with note fingerprints, gold items, strata and labelling provenance.
- Add sealing, disjointness checks and fingerprint export for exclusion by Data Prep and the few-shot set.
- Add taxonomy change requests raised from "not enough categories" evidence.

## Capabilities

### New Capabilities
- `charge-taxonomy`: versioned category list, approval, mapping to standard codes (Level 3), change requests.
- `evaluation-sets`: TEST / DEV / FRESH sets, stratified sampling, sealing, disjointness, label provenance.

### Modified Capabilities
<!-- none -->

## Impact

- New package `itemizer.groundtruth`; files under `${runtime.data_root}/groundtruth` and `taxonomy/` in Git.
- Readers: Classifier (taxonomy), Data Prep (fingerprints), KPI Calculator (labels), Training pipeline (DEV only).
- Depends on `add-common-core-contracts`, `add-version-artifact-registry`. Labelling workflow lives in `add-human-review-system`.
