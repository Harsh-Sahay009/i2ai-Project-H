# Full-export Flash-Lite evaluation — 5 November 2026

The same-model full-export evaluation is **incomplete because of repeated HTTP 503 service errors**. It has responses for **219 of 729 distinct notes**, including the 200-note benchmark cache; **510 notes remain**. There are 1,347 source dispute rows. The evaluator deliberately reports no full-export accuracy or coverage score while inference is incomplete.

## Work performed

- Prepared and froze a separate `all` scope under `data/evaluation/gemini-lite-v1/all/`, using the same Gemini 3.5 Flash-Lite model, prompt, taxonomy, schema, settings and references as the benchmark. The cache is shared within this experiment, so the 200 benchmark notes are reused.
- Initial full run and a cooldown resume each recovered one response before repeated 503 errors. A targeted diagnostic recovered another response. A final recovery pass used transport retry waits of 15, 30 and 60 seconds, retaining the five-second minimum between new request starts; it also ended with repeated 503 errors. This recovered 19 additional notes overall. The extended transport method is recorded in private `recovery_method.json`; no model or prompt tuning was performed.
- All returned answers are retained. The final all-scope snapshot has 217 `ok` results, two `model_unsure` abstentions (the original benchmark cases), and 510 `provider_unavailable` placeholders. The progress counter reaching 729 means the queue ended, not that all notes were answered.
- No full-data score was computed, no model was silently substituted, and no billing upgrade was enabled. No further requests are running or automatically scheduled.

## Resume

From `/Users/harshsahay/.codex/workspaces/i2ai-Project-H`, once service availability recovers:

```bash
.venv/bin/python data/review/run_lite_full_slow_retries.py
```

The private helper preserves the recorded retry method and frozen inputs. An ordinary CLI equivalent, using the adapter's shorter default retries, is:

```bash
.venv/bin/python -m itemizer.independent --model gemini-3.5-flash-lite-free --experiment gemini-lite-v1 --scope all --interval 5 --minutes 60 --run
```

Both reuse existing cache entries. With 510 unanswered notes and a 500-request/day allowance, completion requires more than one fresh daily quota, even before any additional calls needed for rejected responses. Retry after service recovery; preserve one model and one protocol.

## High-value review case

A private, reference-derived resolution candidate is saved at `data/evaluation/gemini-lite-v1/benchmark/high_value_resolution_candidate.json`. Harsh confirmed review of all benchmark labels. The candidate separates $400 already paid from $8,000 still owed. The same note is attached to two $8,000 dispute rows, giving $16,000 original row exposure. Applying the existing repeated-invoice policy to the candidate leaves both rows as explicit discrepancies for duplicate checking. This is a human-assisted candidate, not a successful model extraction; the original automated prediction and benchmark coverage remain unchanged. Duplicate treatment still needs an explicit business decision before automatic acceptance.

## Completed benchmark remains valid within its scope

The 200-note benchmark remains 196/198 exact matches (98.99%), with 196/200 strict yield (98.00%) and user-confirmed human reference review. Its row coverage is 304/307 (99.02%); dollar coverage is 77.33%. Those are benchmark measurements, not full-export figures. Official D3 acceptance remains unassessed.
