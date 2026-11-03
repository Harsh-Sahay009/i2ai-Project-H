## Context

C4 container **Configuration Registry** (components Parameter Schema, Config Resolver, Config Change Log). Placement: **configurable layer**. Position: **controlled**.

## Goals / Non-Goals

**Goals:** every behaviour-changing setting is declared, bounded, owned, logged and hashed into the run.

**Non-Goals:** storing data artifacts (version registry); deciding values (promotion gate, client owner).

## Decisions

- **YAML files in Git + JSON Schema + pydantic-settings.** Git history is the change log backbone; pydantic gives typed access. Alternative: a database-backed config service. Rejected: overkill, harder to diff and review.
- **Parameter metadata in schema:** `owner_role`, `family`, `gate` (`none` | `promotion` | `written_approval` | `locked`), `validity_horizon_days`, `affects_metrics`, `cli_overridable`.
- **Layer precedence:** core defaults < env < carrier override (only keys marked `carrier_overridable`) < CLI (only `cli_overridable`). Carrier overrides resolve per row at classification time; the manifest records the full override map.
- **No silent clamping.** Out-of-range values fail resolution.
- **Gated parameters:** changes to `gate: promotion` keys must reference a published change id; `gate: written_approval` keys (`routing.external_ai_approved`, `data.dataset_class`) need a recorded reference; `gate: locked` keys (such as `guardrails.profile` outside the experiment environment) cannot be changed.
- **Invariants are not parameters.** There is no key to disable evidence verification, the no-edit rule or TEST-label isolation.

## Risks / Trade-offs

- [Too many knobs] → each parameter must name `affects_metrics`; unused parameters are removed at the reuse audit.
- [Carrier overrides fragment behaviour] → overrides limited to vocabulary and thresholds; reported per carrier on the dashboard.

## Open Questions

- Who on the PPG side owns `review.weekly_capacity_rows`? Assumed: review lead (PPG accountant).
