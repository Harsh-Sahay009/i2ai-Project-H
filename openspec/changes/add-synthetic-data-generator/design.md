## Context

C4 container **Synthetic Data Generator**. Architecture doc §9, ADR 0009. Placement: **common core** (test data contract). Position: **owned**.

## Goals / Non-Goals

**Goals:** realistic, labelled, privacy-safe data; adversarial coverage; documented quality.

**Non-Goals:** replacing TEST, DEV or FRESH for client-facing accuracy.

## Decisions

- **Profile from aggregates only.** The profiler runs on team storage and outputs a JSON of distributions; the generator never reads real note text.
- **Grammar-based generation.** Each taxonomy category has phrase templates with slots (qty, rate, amount, invoice); compositions follow the profile's items-per-note distribution. Gold items and offsets are emitted by construction.
- **Noise** from a carrier-style table (abbreviations, misspellings, casing) built from the lexicon, applied at the profile's rates; optional local-LLM paraphrase of templates, followed by gold re-derivation.
- **ADV categories:** direct and indirect injection, misleading "total" statements, unstated amounts, rate × quantity with a wrong stated product, PII bait, contradictory duplicates, decision-request text ("please approve").
- **Quality checks** with thresholds from `synth.*`: JSD per marginal, KS on log-amounts, 8-gram overlap and identifier checks against real notes, rules-only re-derivation, 50-note blind spot check by two people, Spearman correlation SYNTH vs DEV.
- **Repo guard:** pre-commit and CI check reject files containing real-export column signatures or fingerprints in the TEST/DEV lists.

## Risks / Trade-offs

- [Synthetic notes cleaner than real ones] → utility gap reported; noise rates tuned to the profile.
- [Privacy check needs real notes] → runs on team storage only; reports pass/fail and statistics, not text.

## Open Questions

- None.
