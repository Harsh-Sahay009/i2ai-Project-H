## Context

C4 container **Model Router** + **Local Model Runtime** + external **LLM API Provider**. Placement: **common core** for the provider interface and routing contract; route choice and model ids are **configurable layer**. Position: **controlled** (router), **accessed** (models).

## Goals / Non-Goals

**Goals:** replaceable models; fail-closed confidentiality; deterministic reruns; per-call cost.

**Non-Goals:** fine-tuning; prompt content (Classifier's Prompt Builder).

## Decisions

- **Interface:** `complete(request: PromptRequest) -> ProviderResponse` with JSON-schema-constrained output, `usage {tokens_in, tokens_out, latency_ms}`, `model_fingerprint`. Every adapter passes the same contract tests (valid schema output on fixtures, timeout behaviour, error mapping).
- **Default route `local`** (ADR 0003). External only when `routing.external_ai_approved` and `approval_ref` set and masking verified on the payload (gate re-checks for unmasked PII patterns before sending).
- **Model pinning:** local by digest; external by dated snapshot id; aliases rejected.
- **Determinism:** temperature 0 and seed passed when supported; cache key = sha256(prompt bytes, model id+digest, decoding params, schema version). Cache never crosses model versions.
- **Fallback:** retry with backoff up to `routing.max_retries`, then next in `routing.fallback_order`; schema-invalid output counts as failure. Exhausted → classifier marks Review with reason `provider_unavailable`. Never a guessed answer.
- **Cost:** price table version from config; local cost = measured seconds × `kpi.local_cost_usd_per_gpu_hour`.
- **Silent change canary:** 20 fixed DEV notes; response fingerprint per model id stored; a changed fingerprint under the same id raises a `silent_change` event for recertification.
- **Telemetry (action layer):** route, provider, model id, cache hit, retries, fallback, tokens, latency, cost, gate decision.

## Risks / Trade-offs

- [Local model quality lower than API] → measured on DEV/TEST per route; client decides on approval with numbers.
- [Exit cost underestimated] → `substitution_time` recorded whenever a provider is swapped (DEV replay + TEST eval).

## Open Questions

- Will the client approve external AI on masked text? Until then, external adapter is tested only with synthetic notes.
