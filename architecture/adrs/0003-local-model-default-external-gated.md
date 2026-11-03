# 3. Local model by default; external API behind a fail-closed confidentiality gate

Date: 2026-10-31

## Status

Accepted. Amended by [12. Separate train, validation and test sets](0012-train-validation-test-split.md) and [13. The project uses only an anonymized open dataset](0013-anonymized-open-dataset.md).

## Context

Scope external constraints: note text goes to an external AI service only with the client owner's written approval; otherwise a local model or masking.

## Decision

Default route is `local`. The external route requires `routing.external_ai_approved = true` plus an `approval_ref`, and masking is mandatory. The gate fails closed. Both providers sit behind one Provider Interface with shared contract tests.

## Consequences

Provider switching is an exit path, priced as one DEV replay and one TEST evaluation. Local model quality may limit coverage; measured, not assumed.
