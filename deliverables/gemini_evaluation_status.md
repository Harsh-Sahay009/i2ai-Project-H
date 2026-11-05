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
