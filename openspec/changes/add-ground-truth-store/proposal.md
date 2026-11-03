## Why

Accuracy, AUC and every error metric need gold labels, and every prediction needs a category list to be judged against. D1 (charge category list, 12–20 categories, client-approved) and D2 (locked test set, 200 distinct notes, 50 of them blind double-labelled and reviewed by the client, never used to tune) are deliverables in their own right. If test notes leak into tuning, the reported accuracy is meaningless.

## What Changes

- Add a versioned charge taxonomy with definitions, real examples, catch-all category and client approval record.
- Add evaluation sets TRAIN, VALIDATION, TEST (sealed) and FRESH, each with note fingerprints, gold items, strata and labelling provenance.
- Add the split rules (ADR 0012), sealing, disjointness checks and fingerprint export for exclusion by Data Prep and the few-shot set.
- Add taxonomy change requests raised from "not enough categories" evidence.

## Capabilities

### New Capabilities
- `charge-taxonomy`: versioned category list, approval, mapping to standard codes (Level 3), change requests.
- `evaluation-sets`: TRAIN / VALIDATION / TEST / FRESH sets, split rules, sealing, disjointness, label provenance.

### Modified Capabilities
<!-- none -->

## Impact

- New package `itemizer.groundtruth`; files under `${runtime.data_root}/groundtruth` and `taxonomy/` in Git.
- Readers: Classifier (taxonomy), Data Prep (fingerprints), KPI Calculator (labels), Training pipeline (TRAIN and VALIDATION only).
- Depends on `add-common-core-contracts`, `add-version-artifact-registry`. Registers what `add-ground-truth-bootstrap` produces. Later labelling in the UI lives in `add-human-review-system`.
