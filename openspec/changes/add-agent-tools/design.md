## Context

C4 container **Agent Tool Library & MCP Server**. Architecture doc §8.3. Placement: **common core** (one tool contract for every agent). Position: **owned**.

## Goals / Non-Goals

**Goals:** pure, deterministic tools; error codes an agent can act on; docstrings that state when to use and when not to use each tool; read-only analysis over MCP.

**Non-Goals:** tools that write configuration, labels or payments; a public MCP endpoint.

## Decisions

- **Tools are thin wrappers** over the classifier's deterministic components (extractor, evidence verifier, reconciler), so the agent path and the rules path share one implementation.
- **Spans, not numbers.** Tools take character offsets returned by other tools; the agent never passes a number it typed. `compute_rate_times_quantity` and `verify_evidence_span` reject arguments that are not spans from the note.
- **Docstring standard** (§8.3): purpose, Use when, Do not use when, Args, Returns, Errors (code + next action), Determinism, Example. `itemizer tools lint` fails CI on a missing section or on an example that does not run.
- **Schemas** generated from pydantic type hints; the same schemas go to the LLM tool definitions and to MCP.
- **Terminal tools** return `accepted` or a structured rejection; the controller ends the loop on acceptance.
- **MCP server** over stdio, launched by Claude Code from `.mcp.json`; analyst tools are read-only, capped at `mcp.max_rows_per_response`, never return TEST rows, masking maps or raw PPG notes unless the caller runs on team storage with the operator role.
- **Telemetry:** every tool call (name, args hash, result code, latency) is decision telemetry keyed by case id.

## Risks / Trade-offs

- [Too many tools confuse a small local model] → allowlist per agent; tool-selection accuracy measured in agent metrics; prune tools that are never useful.
- [Docstrings drift from behaviour] → docstring examples run as doctests.

## Open Questions

- Should `lookup_abbreviation` be allowed to propose new lexicon entries? Proposed: no; proposals come only from adjudicated cases.
