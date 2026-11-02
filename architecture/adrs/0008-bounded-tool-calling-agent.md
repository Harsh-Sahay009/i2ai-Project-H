# 8. Itemization as a bounded tool-calling agent

Date: 2026-10-31

## Status

Accepted. Refines the classifier design; ADR 0006 invariants still apply.

## Context

The course requires an agentic solution with at least five custom tools that make an LLM agent's behaviour more deterministic. Single-shot prompting asks the model to do arithmetic, quote evidence and choose categories in one pass, and amounts are the most costly errors.

## Decision

The classifier runs a bounded ReAct-style agent (Yao et al., 2023) on the pretrained LLM:

- Eight deterministic pipeline tools do all extraction, arithmetic, lookup, verification and reconciliation.
- Two terminal tools (submit, escalate) are the only way out of the loop.
- Step and call budgets, temperature 0, pinned model, transcript-keyed cache.
- The rules-only route remains as baseline and fallback.

Analyst tools are exposed read-only over MCP.

## Consequences

More model calls per note (cost and latency are measured as agent metrics). Behaviour is explainable through the trace. The tools are reused by the team's and the client's agents.
