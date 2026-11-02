## Why

PPG data cannot appear in the public GitHub repo, the poster or the live demos, and unit tests and guardrail tests need many labelled notes, including adversarial ones that do not exist in the sample. The course requires explaining how simulated data quality is ensured.

## What Changes

- Aggregate Profiler over real data (aggregates only).
- Charge Phrase Grammar producing notes with gold items by construction; Noise Injector; Adversarial Case Generator.
- Synthetic Quality Checker: fidelity, privacy, validity, utility; publication only on pass.
- SYNTH and ADV registered as evaluation-set kinds; CI guard against real-data commits.

## Capabilities

### New Capabilities
- `synthetic-data`: generation, quality checks, publication, labelling, repo guard.

### Modified Capabilities
<!-- none -->

## Impact

- New package `itemizer.synth` (Faker, SciPy); published sets under `data/synthetic/` in Git.
- Used by tests, demos, add-guardrails, add-guardrail-evaluation, add-web-ui demo mode.
