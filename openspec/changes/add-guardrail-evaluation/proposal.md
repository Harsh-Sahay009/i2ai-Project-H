## Why

The course asks how the model behaves with versus without the safety guardrails. A claim that guardrails help needs paired, reproducible measurements on the same agent, model, prompt and data, plus agent-behaviour metrics that show what the tools changed.

## What Changes

- An `experiment` environment that accepts only SYNTH and ADV data and cannot publish.
- Guardrail Ablation Evaluator: runs profiles `full`, `none` and single-guard-off; reports invented-amount, edited-amount, unverifiable-evidence, injection-success, PII-egress and prohibited-action rates alongside accuracy, coverage, cost and steps.
- Agent Behaviour Metrics: tool calls per note, invalid calls, terminal compliance, step-budget hits, resubmissions.
- Trace pairs for the poster and demo.

## Capabilities

### New Capabilities
- `guardrail-evaluation`: experiment environment, ablation runs, paired statistics, agent metrics, trace pairs.

### Modified Capabilities
<!-- none -->

## Impact

- Adds components to the KPI Calculator (`itemizer.kpi.ablation`, `itemizer.kpi.agent_metrics`); new env file `config/env/experiment.yaml`.
- Depends on add-guardrails, add-synthetic-data-generator, add-kpi-calculator, add-itemization-classifier.
