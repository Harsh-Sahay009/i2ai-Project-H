## Why

The slide's "Training Algorithm" closes the loop from KPIs and reviews back into the classifier. With ~1,350 rows, the right lever is not weight training but versioned changes to the configurable layer: lexicon, few-shot set, prompt, thresholds and calibration. The atlas closed loop requires each change to come from adjudicated cases, be replayed, pass a gate and ship under a version tag with an owner, evidence, rollback and a validity horizon. The locked test set must never tune the tool.

## What Changes

- Closed Case Miner over eligible cases (AI wrong, context changed) from TRAIN and PROD.
- Candidate Change Generator for lexicon entries, few-shot swaps, prompt edits and taxonomy change requests.
- Threshold Calibrator fitting the calibration map and Review thresholds on VALIDATION.
- Replay Runner comparing current vs candidate on replay packs and VALIDATION.
- Promotion Gate using VALIDATION scores, never TEST, and requiring operator approval.
- Change Publisher and Recertification Scheduler.

## Capabilities

### New Capabilities
- `calibration-loop`: case mining, candidate generation, calibration, replay.
- `promotion-gate`: evidence requirements, publication with owner/evidence/version/rollback/horizon, rollback, recertification.

### Modified Capabilities
<!-- none -->

## Impact

- New package `itemizer.improve`.
- Depends on telemetry store, ground truth (TRAIN and VALIDATION only), router, KPI Calculator, configuration registry, version registry.
