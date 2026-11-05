# OpenAI evaluation under a $5 total authorization

The user authorized up to $5 total and asked us to configure the supplied API key locally. Use a separate worktree and experiment; preserve the Gemini source and frozen results. A read-only model-access check succeeded for `gpt-5.4-mini-2026-03-17`.

Use the same prompt, taxonomy, schema, dataset and 200 human-reviewed reference labels. First complete the 200-note benchmark; proceed to all 729 notes only if strict yield exceeds 90%, while reporting the 95% project target separately. No model mixing or tuning against partial scores.

Reuse the existing OpenAI-compatible adapter, translating its outgoing `max_tokens` to `max_completion_tokens` in a paid transport wrapper. Omit temperature for medium reasoning. Pin the exact model snapshot, standard service tier, store=false, and official rates: input $0.75/M, cached input $0.075/M, output $4.50/M. Source: https://developers.openai.com/api/docs/models/gpt-5.4-mini . The documented context limit is 400,000 tokens.

Before every outbound generation attempt, including transport retries, persist a reservation of the maximum context-window input charge plus the requested maximum output charge. A process/file lock serializes reservation and settlement. After a valid metered response replace the reservation with its actual token charge. Retain the reservation on HTTP/transport errors, missing usage or a crash. Refuse a request when its reservation would exceed the authorized total. This conservative method may stop below $5. It bounds this evaluation's calls, not unrelated account activity, taxes or changes to provider pricing.

Store authorization and a single persistent ledger under ignored `data/evaluation/`, shared across development, benchmark and full-data phases. Validate the ledger identity, totals, cap and pinned rates; fail closed on malformed records. Keep secrets out of protocol, reports, tests and Git. A free-model run keeps its existing adapter and behavior.

Implement meaningful tests for pre-call reservation, response settlement, restart accounting, denied requests sending no HTTP call, retained failure reservations, malformed usage, locking, pinned wire parameters and configuration mismatch. Test before real inference. Incomplete inference must not produce an accuracy score. All outputs remain private except aggregate reports and code.
