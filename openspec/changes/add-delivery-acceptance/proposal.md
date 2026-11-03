## Why

The other changes build components, but no task checks that D3 and D4 meet their done-when conditions, and no task writes D5. `add-run-console` refers to a D4 acceptance script that nothing builds. The scope also asks PPG for two baseline numbers, and no task tracks them. D5 must let a reader outside the team rerun the tool, and nothing defines how, since the dataset is not published.

## What Changes

- `itemizer acceptance d3` and `itemizer acceptance d4`: run the checks from the scope and write an evidence summary.
- Record that Jake has seen the prototype, with the date and evidence.
- Track the requests to PPG: current minutes per dispute, monthly dispute volume, and confirmation of the dataset.
- Generate the D5 tables from KPI snapshots, with honest labels, error examples and rerun instructions. The team writes the prose.
- Verify the rerun instructions with a dry run by someone who did not write them.

## Capabilities

### New Capabilities
- `deliverable-acceptance`: D3 and D4 checks, client review record, client request tracking.
- `methodology-report`: D5 content, labels, error examples, rerun path.

### Modified Capabilities
<!-- none -->

## Impact

- New packages `itemizer.acceptance` and `itemizer.report`; template under `report/`; request tracking in `deliverables/requests.yaml`.
- Depends on add-run-console, add-kpi-calculator, add-output-formatter and add-version-artifact-registry.
- C4: components Acceptance Runner (Run Console) and Methodology Report Builder (KPI Dashboard).
