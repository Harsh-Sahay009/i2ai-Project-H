## ADDED Requirements

### Requirement: Three skills
The repository SHALL contain `skills/itemizer-weekly-review/`, `skills/itemizer-analyst/` and `skills/itemizer-dev/`, each with a `SKILL.md` and a `templates/` folder.

#### Scenario: Structure check
- **WHEN** `itemizer skills lint` runs
- **THEN** it confirms all three folders, their SKILL.md files and at least one template each

### Requirement: SKILL.md content
Each SKILL.md SHALL have front matter with name and description, and sections When to use, When not to use, Inputs, Steps, Tools, Stop and ask a person when, and Outputs.

#### Scenario: Missing stop section
- **WHEN** a SKILL.md lacks "Stop and ask a person when"
- **THEN** the lint fails

### Requirement: Tool references resolve
Every tool named in a skill SHALL exist in the Tool Registry or the CLI.

#### Scenario: Renamed tool
- **WHEN** a skill references `explain_case` but the tool is `explain_row`
- **THEN** the lint fails naming the skill and tool

### Requirement: Reserved decisions stated
Each skill SHALL list the decisions reserved for people and the data it must never output.

#### Scenario: Analyst skill
- **WHEN** an agent follows the analyst skill to a taxonomy gap
- **THEN** the skill directs it to draft a change request and stop for client approval

### Requirement: Templates
The skills SHALL provide templates for weekly summary, discrepancy follow-up, error review report, taxonomy change request, ADR, published change record and guardrail test case.

#### Scenario: Error review report
- **WHEN** an analyst fills the error review template with an agent
- **THEN** the report has sections per error type a–g with n, examples (non-TEST) and proposed actions
