## Context

Requirement 4; architecture doc §8.5–8.6. Placement: **common core** for workflow instructions; carrier- or site-specific notes stay **local exception** inside a skill's `notes/`.

## Goals / Non-Goals

**Goals:** an agent following a skill uses the right tools in the right order and stops where a person must decide.

**Non-Goals:** skills that change configuration or labels.

## Decisions

- **Format:** each skill folder has `SKILL.md` with YAML front matter (`name`, `description` stating when to use it), sections When to use / When not to use / Inputs / Steps / Tools / Stop and ask a person when / Outputs, and a `templates/` folder.
- **Guardrails in skills:** every skill lists the decisions reserved for people (payment, approving taxonomy, publishing changes) and the data it must never output (TEST rows, names).
- **Templates:** weekly summary, discrepancy follow-up, error review report, taxonomy change request, ADR, published change record, guardrail test case.
- **Lint:** `itemizer skills lint` checks front matter, required sections and that every referenced tool exists in the registry.

## Risks / Trade-offs

- [Skills drift from the tools] → lint in CI.

## Open Questions

- Which agent will PPG use (Claude, Copilot, other)? The format is plain Markdown so it works with any agent that reads skills.
