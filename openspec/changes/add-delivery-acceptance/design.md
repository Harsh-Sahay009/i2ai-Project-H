## Context

C4 components **Acceptance Runner** (Run Console) and **Methodology Report Builder** (KPI Dashboard). Placement: **common core**, since one check applies to every build. Position: **owned**.

Authority: the checks report; they decide nothing. Whether D3 and D4 are accepted stays with the team and the client owner.

## Goals / Non-Goals

**Goals:** D3 and D4 done-when conditions checked by one command; every number in D5 traceable to a KPI snapshot; a rerun path an outsider can follow.

**Non-Goals:** computing metrics (KPI Calculator).

## Decisions

- **Report gate status as written.** The acceptance summary copies status, point estimate, interval and n from the KPI snapshot. A level is met when the measured value reaches the target, and the interval is always shown beside it. The team chose this rule; the client owner still needs to confirm it.
- **D3 check.** Runs the pipeline end to end on the sample export, then reports the Level 1 gate on TEST. D3 stays `open` until a review record shows Jake has seen it.
- **D4 check.** One command on an export not used to build the tool. Under ADR 0013 that is a synthetic export unless PPG provides another file. It checks the 30-minute limit at 1,500 rows, the `Items` and `Row Summary` sheets, and the Level 2 gate on TEST. Numbers from a synthetic export are labelled synthetic and never count toward accuracy.
- **Generated tables, written prose.** The builder produces the measures, error examples and rerun steps. The team writes the method and discussion. Target length is 8 to 12 pages.
- **Two rerun paths.** A reader with the dataset and the response cache reproduces the reported numbers. A reader without them runs the same commands on published synthetic data and compares with the published synthetic results. The report states clearly that the second path does not reproduce the accuracy numbers.
- **Versions and telemetry.** Versions: acceptance results and the report, each with the KPI snapshot ids they cite. Telemetry: acceptance runs are ordinary runs with their own action telemetry.

## Risks / Trade-offs

- [Outside rerun fails late] → dry run scheduled before 3 Dec, not on the last day.
- [PPG baseline never arrives] → the report says so and gives no saving estimate.
- [Report numbers go stale] → tables are regenerated from named snapshots at the final freeze.
- [The response cache contains note text] → it is shared with the dataset on request and is not published.

## Open Questions

- Who outside the team does the dry run.
