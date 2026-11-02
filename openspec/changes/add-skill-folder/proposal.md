## Why

The course requires a skill folder with a `SKILL.md` and templates that the team used to build the solution or that the client can use later. Skills turn the project's repeated workflows (weekly review, run analysis, spec-driven development) into instructions any LLM agent can follow consistently with the custom tools.

## What Changes

- `skills/itemizer-weekly-review/` (client): SKILL.md for running and reviewing a weekly export, templates for the weekly summary and discrepancy follow-up.
- `skills/itemizer-analyst/` (client and team): SKILL.md for analysing runs with the MCP analyst tools; templates for an error review report and a taxonomy change request.
- `skills/itemizer-dev/` (team): SKILL.md for the spec-driven workflow (atlas → C4 → OpenSpec → apply → verify), templates for an ADR, a published change record and a guardrail test case.
- A lint check for skill structure and tool references.

## Capabilities

### New Capabilities
- `skill-folder`: skill structure, content requirements, templates, linting.

### Modified Capabilities
<!-- none -->

## Impact

- New top-level `skills/` folder; symlinked or copied into `.claude/skills/` for Claude Code.
- Depends on add-agent-tools (tool names), add-web-ui (UI steps), add-kpi-calculator (metric names).
