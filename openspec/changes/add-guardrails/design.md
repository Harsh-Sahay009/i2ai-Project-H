## Context

C4 container **Guardrail Layer**. Architecture doc §8.4, ADR 0010. Placement: **common core**. Position: **controlled** (policy and logging).

## Goals / Non-Goals

**Goals:** fail closed; every block explained and logged; measurable effect.

**Non-Goals:** content moderation beyond this domain; replacing the evidence verifier (the Output Guard calls it).

## Decisions

- **Input Guard.** Note text inside `<untrusted_note>` delimiters with a system rule that it is data. Detector: pattern rules (imperatives aimed at the assistant, role words, "ignore", "system", tool names, URLs) plus a small classifier trained on ADV-train only (scored on ADV-test). Above `guardrails.injection_detector_threshold` → items may still be proposed, but the row is Review with reason `possible_injection`.
- **Tool-Call Guard.** Rejects calls outside `agent.tool_allowlist`, invalid arguments, a repeat of an identical call, and calls beyond per-tool limits; enforces `agent.max_steps`.
- **Output Guard.** Runs the core invariant validators, checks every amount traces to a tool result in the transcript, checks categories are in the taxonomy; allows `agent.max_resubmits` corrections, then Review.
- **Action Guard.** No tool exists for payment or approval; the guard also scans rationales for decision language ("approve", "pay", "valid charge") and strips it from outputs, recording `prohibited_action_attempt`.
- **Privacy Guard.** PII regex + NER on every payload to a model or MCP client; blocks and routes to fallback.
- **Profiles.** `full` (default, locked in dev and prod); `none` and single-guard-off only when environment is `experiment`.
- **Telemetry.** Guard decisions (`allow`, `block`, `quarantine`, `resubmit`, `strip`) with reason codes, shown in the Agent Trace Viewer.

## Risks / Trade-offs

- [Injection detector false positives lower coverage] → measured on SYNTH (clean) as false-positive rate; threshold is a promotion-gated parameter.
- [Determined injection evades detection] → amounts still come only from tools and evidence must be verbatim, so a successful injection cannot create an amount.

## Open Questions

- None.
