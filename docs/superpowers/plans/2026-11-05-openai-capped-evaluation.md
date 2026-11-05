# OpenAI capped evaluation implementation plan

> Execute inline using the executing-plans skill; user authorized the separate comparison and $5 total. Existing Gemini worktree remains unchanged.

**Goal:** Run a reproducible OpenAI comparison within one persistent $5 evaluation allowance.

**Architecture:** `paid.py` wraps existing HTTP transport with a locked persistent reserve/settle ledger. `independent.py` selects it only for the explicitly configured direct OpenAI model and records its spending summary. Model configuration pins the snapshot and official rates.

**Tech stack:** Python, Decimal, fcntl, existing urllib transport and pytest.

- [ ] Add `tests/test_paid.py`: exercise `CappedOpenAITransport(spec, ledger, limit, transport)` as a callable. In a fake response's transport assert the reservation already exists; return usage with 100 prompt/10 completion tokens. Assert settlement is `$0.00012`. Recreate the wrapper and verify prior calls remain counted. An allowance below the per-call reservation must raise before transport invocation. HTTP failures retain reservations; malformed usage cannot release them. Verify modern token field, store=false and standard tier.
- [ ] Run the new tests and observe expected feature-missing failure. Implement `src/itemizer/paid.py` with exact model/rate validation, atomic ledger writes, file locking and per-attempt bounds. Run the paid tests and correct only observed failures.
- [ ] Add the pinned model to `config/models.yaml`. In `independent.py`, add `--max-usd`, positive finite validation, and paid authorization/factory selection. Retain the shared ledger for all scopes. Extend protocol with requested run budget and spending policy; record ledger summary in complete and incomplete outputs.
- [ ] Run provider/independent/paid tests and the complete relevant baseline. Check Git diff and verify no private paths or secrets tracked. Create private dataset-scoped $5 authorization from the user's reply and dry-run the benchmark protocol. Confirm the original Gemini worktree still matches its frozen protocol.
- [ ] Run benchmark with `PYTHONPATH=src .venv/bin/python -m itemizer.independent --model openai-gpt-5.4-mini --experiment openai-mini-v1 --interval 1 --max-usd 5 --run`. Report progress without inspecting partial scores. On completion report exact agreement, strict yield, abstentions, coverage, errors, confidence intervals and actual/conservatively held spend.
- [ ] If strict benchmark yield is above 90%, run the same command with `--scope all --minutes 60`, reusing the same candidate cache and spend ledger. Stop at provider failure or the cap. Preserve full-data coverage separately from benchmark accuracy; document remaining human/duplicate review.
