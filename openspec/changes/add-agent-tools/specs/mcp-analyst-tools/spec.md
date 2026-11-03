## ADDED Requirements

### Requirement: Read-only analyst tools over MCP
The MCP server SHALL expose `get_run_summary`, `explain_row`, `list_error_cases`, `get_kpi_snapshot` and `draft_taxonomy_change_request`, and none of them SHALL modify configuration, labels, predictions or review decisions.

#### Scenario: Claude Code asks why a row was flagged
- **WHEN** Claude Code calls `explain_row(run_id, row_id)`
- **THEN** it receives the outcome, the rule that fired, the tool-call trace summary and evidence spans

### Requirement: Data restrictions
MCP tools MUST NOT return TEST or VALIDATION rows or person names, and SHALL cap list results at `mcp.max_rows_per_response`.

#### Scenario: Errors on TEST
- **WHEN** `list_error_cases` is called for a TEST or VALIDATION evaluation
- **THEN** the tool returns aggregates only

### Requirement: Drafts, not changes
`draft_taxonomy_change_request` SHALL produce a draft document with evidence links and SHALL NOT change the taxonomy.

#### Scenario: Draft for "yard fee"
- **WHEN** an analyst asks for a change request for "yard fee"
- **THEN** a draft is written under `drafts/` listing affected notes by fingerprint and dollar share

### Requirement: Logged access
Every MCP tool call SHALL be logged with tool name, caller role and argument hash.

#### Scenario: Audit
- **WHEN** an operator reviews MCP usage
- **THEN** each call appears with time, tool and role
