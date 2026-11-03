## ADDED Requirements

### Requirement: Step-by-step agent trace
For a selected row, the Agent Trace Viewer SHALL show each LLM turn, each tool call with its arguments and result, each guard decision and the terminal tool, read only from decision telemetry.

#### Scenario: Rejected submission
- **WHEN** an operator opens a row whose first submission the Output Guard rejected
- **THEN** the trace shows the rejected submission, the rejection reason and the resubmission or the move to Review

### Requirement: Trace access follows data limits
The viewer MUST NOT show traces for TEST or VALIDATION rows unless `ui.test_error_examples_released` is true for TEST, and MUST NOT be available in a blind labelling session.

#### Scenario: Trace for a TEST row
- **WHEN** an operator requests the trace of a TEST row before release
- **THEN** the request is refused and logged

### Requirement: Tool reference page
The Tool Reference page SHALL list every registered agent tool with its docstring and schema, read from the Tool Registry.

#### Scenario: New tool registered
- **WHEN** a tool is added to the Tool Registry
- **THEN** it appears on the page with no change to the page's template
