## Why

The itemization agent must not do arithmetic, guess abbreviations or quote from memory. Deterministic tools with docstrings written for LLM readers make its behaviour predictable and verifiable, and the course requires at least five custom agentic tools. The same tools, served read-only over MCP, give the team (Claude Code) and the client an agentic way to analyse runs.

## What Changes

- Eight pipeline tools: `extract_money_spans`, `lookup_abbreviation`, `get_charge_categories`, `compute_rate_times_quantity`, `verify_evidence_span`, `reconcile_row`, `submit_itemization` (terminal), `escalate_to_review` (terminal).
- Five read-only MCP analyst tools: `get_run_summary`, `explain_row`, `list_error_cases`, `get_kpi_snapshot`, `draft_taxonomy_change_request`.
- A Tool Registry that generates JSON schemas from type hints and lints docstrings against a fixed standard.
- An MCP server (stdio) for Claude Code and the client's agent.

## Capabilities

### New Capabilities
- `agent-tools`: pipeline tools, docstring standard, registry, determinism guarantees.
- `mcp-analyst-tools`: read-only MCP tools, permissions, limits.

### Modified Capabilities
<!-- none -->

## Impact

- New packages `itemizer.agent_tools` and `itemizer.mcp`; dependency on the MCP Python SDK.
- Used by add-itemization-classifier; screened by add-guardrails; documented in add-skill-folder.
- C4 container `agentTools` (`Components-AgentTools` view).
