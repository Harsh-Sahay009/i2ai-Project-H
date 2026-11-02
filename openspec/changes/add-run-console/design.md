## Context

C4 container **Run Console** (CLI Commands, Pipeline Orchestrator, Run Manifest Builder). The Web UI launches runs through this CLI (ADR 0007), so there is exactly one orchestrator. Placement: **common core**. Position: **controlled**.

## Goals / Non-Goals

**Goals:** one command; frozen manifest before stage 1; resumable; clear exit codes for scripting.

**Non-Goals:** UI pages (add-web-ui); scheduling (weekly runs are launched by a person).

## Decisions

- **Typer** for commands; `rich` for progress. Alternative: Click directly; Typer is thinner over it.
- **Stage graph** with checkpoints written to the version registry every `runtime.checkpoint_every_notes`; `--resume <run_id>` continues.
- **Budgets:** abort gracefully when `budget.max_minutes_per_run` or `budget.max_usd_per_run` is exceeded; unprocessed rows end as Review with reason `budget_exhausted`, never dropped.
- **Exit codes:** 0 success, 2 config/manifest error, 3 input contract error, 4 budget exhausted (output still written), 5 gate failure (evaluate/promote).
- **Telemetry:** stage start/end, durations, row counts (action layer).

## Risks / Trade-offs

- [Local model too slow for 30 min] → note deduplication + concurrency; measured in D3; fallback to rules-only route for the remainder flagged Review.

## Open Questions

- None.
