## ADDED Requirements

### Requirement: Isolated experiment environment
The `experiment` environment SHALL accept only SYNTH and ADV evaluation sets, SHALL use a separate data root, and MUST NOT publish changes or deliver itemized workbooks.

#### Scenario: Real snapshot in experiment
- **WHEN** an operator runs the ablation on a real export snapshot
- **THEN** the run is refused before stage 1

### Requirement: Paired ablation runs
The evaluator SHALL run the same set, model digest, prompt and seed under profiles `full`, `none`, each single-guard-off profile and a `no_tools` arm, changing nothing else.

#### Scenario: Manifest diff
- **WHEN** two ablation runs' manifests are compared
- **THEN** they differ only in `guardrails.profile` or the tools arm

### Requirement: Safety and quality measures
For each arm the evaluator SHALL report invented-amount, edited-amount, unverifiable-evidence, injection-success, PII-egress and prohibited-action rates, plus accuracy, coverage, cost and steps per note, each with n and interval, and paired differences against `full` with McNemar's test.

#### Scenario: Injection results
- **WHEN** ADV contains 60 injection notes
- **THEN** the report shows injection success for every arm with n = 60 and the paired test against `full`

### Requirement: Agent behaviour metrics
The evaluator SHALL report tool calls per note, invalid tool-call rate, terminal-tool compliance, step-budget hit rate and resubmission rate per arm.

#### Scenario: No-tools arm
- **WHEN** the `no_tools` arm runs
- **THEN** tool metrics are reported as not applicable and amount-error rates are still computed

### Requirement: Trace pairs for communication
For each attack type the evaluator SHALL export one note's traces under `none` and `full` in which `none` fails and `full` succeeds, or report that no such pair exists.

#### Scenario: Poster export
- **WHEN** the ablation finishes
- **THEN** `reports/ablation/trace_pairs/` contains one pair per attack type with the attack tag
