# 10. Guardrail ablation only in an isolated experiment environment

Date: 2026-10-31

## Status

Accepted. Narrow exception to ADR 0006.

## Context

Requirement 7a asks to show how the model behaves with and without guardrails. ADR 0006 makes invariants non-configurable.

## Decision

`guardrails.profile` may be `none` or single-guard-off only when `environment = experiment`. That environment:

- accepts only SYNTH and ADV data (checked by fingerprint and set kind),
- uses a separate data root,
- cannot write outputs to the accountant workbook path or publish changes,
- stamps every artifact "ablation".

In dev and prod the profile is locked to `full`.

## Consequences

The with/without comparison runs on the same agent, model and seed, without ever exposing PPG data or production outputs to unguarded behaviour.
