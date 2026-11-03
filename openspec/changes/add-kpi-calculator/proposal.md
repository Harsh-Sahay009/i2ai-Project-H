## Why

The project is judged by numbers: coverage and ≥95% accuracy per level, plus the agreed error list (bad classification, wrong counts, not enough categories, reproducibility, low confidence, wrong amounts) and success list (accuracy, cost of inference, verification text, AUC, approval rate). Those numbers are easy to get wrong: mixing the locked test set with tuning data, scoring notes instead of rows, ignoring the test set's oversampling, comparing runs under different definitions, or reporting a point estimate from 200 notes without an interval. D5 requires every measure with its sample size and a rerunnable method.

## What Changes

- Metric Definition Registry (versioned YAML) for every error and success metric with formula, unit, population, label source, matching rule, weighting, interval method and target.
- Evaluation Set Resolver with population separation (TRAIN, VALIDATION, TEST, FRESH, PROD) and TEST-label isolation.
- Item Matcher (optimal assignment on category + amount tolerance) and Error Taxonomy Classifier.
- Metric Engine, Stratum Weighter, Uncertainty Estimator, Level Gate Evaluator, Loop Health Meter.
- Per-carrier coverage and accuracy, and the Level 3 cost-driver summary by carrier and category.
- Immutable KPI snapshots keyed by every version they depend on; TEST peek budget for Level gates.

## Capabilities

### New Capabilities
- `kpi-metrics`: definitions, populations, matching, error and success metrics, weighting, intervals, snapshots, reproducibility.
- `level-gates`: Level 1/2/3 evaluation, TEST peek budget, VALIDATION-only results for promotion.

### Modified Capabilities
<!-- none -->

## Impact

- New package `itemizer.kpi`; `metrics/definitions.yaml`, `metrics/prices.yaml` in Git; snapshots in DuckDB + CAS.
- Depends on core contracts, version registry, ground truth, telemetry store, configuration registry (evaluation family).
- Feeds the dashboard, the promotion gate and D5.
