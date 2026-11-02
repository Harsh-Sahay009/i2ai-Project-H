## Why

An LLM agent that reads carrier-written text can be manipulated (indirect prompt injection), can invent or nudge amounts, leak names, loop, or overstep into payment decisions. Each of these harms PPG directly. The course requires safety guardrails for risks and ethical concerns, and evidence of their effect.

## What Changes

- Input Guard: untrusted-note wrapping, control-sequence stripping, injection detection and quarantine to Review.
- Tool-Call Guard: allowlist, argument validation, step and call budgets, duplicate-call detection, terminal-tool requirement.
- Output Guard: schema, verbatim evidence, no-edit, amounts from tools, category in taxonomy; one resubmission.
- Action Guard: blocks payment, approval and data-changing actions or language.
- Privacy Guard: PII screen for model-bound and MCP-bound payloads.
- Guardrail Profile Resolver: `full` locked outside the experiment environment.

## Capabilities

### New Capabilities
- `guardrails`: the five guards, their decisions, telemetry and profile control.

### Modified Capabilities
<!-- none -->

## Impact

- New package `itemizer.guardrails`.
- Used by add-itemization-classifier and add-agent-tools (MCP); evaluated by add-guardrail-evaluation.
- C4 container `guardrails`.
