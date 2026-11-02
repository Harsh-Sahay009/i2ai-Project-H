## Why

Thresholds, prompts, vocabulary, routing and review policy differ by environment and carrier while the pipeline structure stays the same. The atlas calls this the configurable layer and warns that every setting needs limits, an owner and a log, or it becomes configuration debt that moves behaviour while code stays the same.

## What Changes

- Add a typed Parameter Schema covering every parameter in `architecture/docs/03-configurable-layer.md` (families: thresholds, prompting, vocabulary, routing, workflow, evaluation, runtime).
- Add a Config Resolver with layers core → environment → carrier override → CLI flag, limit validation and a frozen, hashed effective config.
- Add an append-only Config Change Log and validity horizons per published value.
- Mark promotion-gated and approval-gated parameters; refuse direct edits to them.

## Capabilities

### New Capabilities
- `configuration-registry`: declaration, resolution, validation, hashing, change logging and horizons for all configurable parameters.

### Modified Capabilities
<!-- none -->

## Impact

- New package `itemizer.config`; files under `config/` (`schema/`, `core/`, `env/`, `carriers/`).
- Consumed by Run Console, Router, Classifier, Review System, KPI Calculator, Training pipeline.
- Depends on `add-common-core-contracts` (manifest records the config hash).
