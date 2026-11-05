# Gemini evaluation status — 5 November 2026

Gemini access is configured using the user-provided local credential. It is stored only in ignored `.env`, with mode 0600. No credentials or supplied curl command were displayed, executed, or committed. Model discovery and harmless inference succeeded. No billing upgrade or local model download was performed.

The independent evaluator uses `gemini-3-flash-preview`, medium effort, temperature 0, the existing taxonomy/prompt/examples, and the immutable 200-note received draft benchmark. `gemini-3.8-flash` had service-availability problems during development checks and was not used for the benchmark. The selected model passed a full-prompt/schema check before benchmark scoring. New/affected checks pass: 125 tests; independent code review found no blockers.

## Current run

- Experiment: `data/evaluation/gemini-free-v2/benchmark/`.
- Responses cached: **20 of 200**; **180 remain**. These are saved inference responses, not a completed accuracy result.
- The provider returned repeated **HTTP 429** responses. Resuming after a cooldown recovered one more response, then hit 429 again. Further calls were stopped. The account's requests-per-minute and requests-per-day limits still need confirmation in AI Studio.
- Accuracy: **not reported**. The evaluator refuses to score an incomplete run.
- References: all 200 remain model drafts; no human check, client approval, historical freeze, or D3 completion was asserted.

The initial stopped passes and transport diagnostics are preserved privately. Cached answers were reused under the same fixed model/prompt/schema; no partial agreement scores were inspected or used to choose settings. A private recovery helper spaced new requests and recorded HTTP status codes without note contents or credentials. Input-quality inspection found no raw-text variants within normalized note groups.

## Resume after quota permits

From `/Users/harshsahay/.codex/workspaces/i2ai-Project-H`:

```bash
.venv/bin/python -m itemizer.independent --experiment gemini-free-v2 --run
```

This reuses cached answers; it does not require Alejandro's historical freeze records. Do not change the model/prompt/reference file during a fixed run. Confirm the applicable RPM and RPD in Google AI Studio before resuming; adjust execution pacing within the recorded method or create an explicit new version if configuration changes. Do not activate paid billing to bypass the user's free-only constraint.

Once all 200 predictions are available, report exact agreement with model drafts, coverage and abstentions, errors by category/amount/missing/extra, confidence intervals and runtime. Benchmark-row coverage is not full-export coverage. Human reference review is still required to establish real accuracy.

## Account limits confirmed and separate Flash-Lite candidate

The user supplied the AI Studio rate-limit view: Gemini 3 Flash and Gemini 3.8 Flash each have 5 RPM and 20 RPD; Gemini 3.5 Flash-Lite and Gemini 3.1 Flash-Lite each have 15 RPM and 500 RPD. The supplied usage view is a 28-day peak display, so its usage numerators are not a live remaining-balance calculation. Google documents daily resets at midnight Pacific (3 a.m. New York on this date). Original Flash inference remains stopped; merely slowing requests cannot clear an exhausted daily quota. Its private recovery helper now uses a conservative 13-second interval for any future authorized resume after reset.

The user explicitly selected **Evaluate Flash-Lite separately for free**. A new candidate, `gemini-3.5-flash-lite-free`, uses the same extraction prompt, schema and reference benchmark with medium effort and temperature 0. Selection was based on available free quota, not observed benchmark accuracy. No original Flash answers are mixed into this candidate's cache or results. The full-prompt development check (outside the benchmark) succeeded in 5.2 seconds with no grammar violations. Existing/new affected tests: 125 passed.

The fixed separate run is:

```bash
.venv/bin/python -m itemizer.independent --model gemini-3.5-flash-lite-free --experiment gemini-lite-v1 --interval 5 --run
```

Its protocol and private outputs are in `data/evaluation/gemini-lite-v1/benchmark/`, with a separate cache under that experiment. Five seconds between request starts is approximately 12 RPM, below the account's 15-RPM limit, before any transport retries. Any provider interruption still prevents a final accuracy claim. The 200-note benchmark is the first phase; full-export coverage remains a separate measurement. The results are not assumed to meet the quality target simply because the model runs.
