## Context

KPI Calculator components **Guardrail Ablation Evaluator** and **Agent Behaviour Metrics**. ADR 0010. Metric definitions in architecture doc §4.7b.

## Goals / Non-Goals

**Goals:** fair, paired, reproducible with/without comparison; results usable on the poster and in D5.

**Non-Goals:** running unguarded behaviour on PPG data or in prod.

## Decisions

- **Isolation.** `experiment` env: separate data root, input sets limited to kinds SYNTH and ADV (checked), outputs stamped "ablation", publication and workbook delivery disabled.
- **Paired design.** Same set version, model digest, prompt, seed and cache policy (cache off so each profile actually calls the model); only `guardrails.profile` changes.
- **Without guards means without enforcement, not without tools.** In `none` the agent still has its tools but outputs are accepted as emitted, so the measure isolates the guards. An extra `no_tools` arm (single-shot prompt) isolates the value of the tools.
- **Statistics.** Per-note paired failure indicators; McNemar's test and bootstrap intervals on rate differences; n per attack type.
- **Trace pairs.** For each attack type, the run picks one note where `none` fails and `full` succeeds and exports both traces for the poster and the code demo.

## Risks / Trade-offs

- [Results depend on the small local model] → repeat with the hosted model if approved; report both.

## Open Questions

- None.
