# 9. Protecting client data and simulating test data (requirement 6)

## 9.1 Protection of PPG data

| Control | Implementation |
|---|---|
| Storage | Encrypted volume on a team-controlled server; CAS refuses any other root |
| Model access | Local model by default; external API only with written approval + masking + fail-closed gate |
| Masking | Regex + pretrained NER; stable placeholders; reversal map kept separately |
| Least privilege | Role map in Web UI and MCP; TEST labels readable only by the KPI Calculator |
| No PII in telemetry | Fingerprints instead of text; pseudonymous reviewer ids |
| Public artifacts | GitHub repo, poster, demos and slides use **synthetic data only**; a CI check rejects commits containing files that match real-export fingerprints or column signatures |
| Retention | Client instruction at project end; deletion leaves logged tombstones |

## 9.2 Synthetic data generator

Two sets are produced and versioned like any evaluation set:

* **SYNTH**: realistic notes for demos, unit tests and the public repo.
* **ADV**: adversarial notes for guardrail tests (injection, misleading totals, PII bait, contradictory rates, unstated amounts).

Generation:

1. **Aggregate profile** computed on team storage: category mix, items per note, amount distributions per category, note length, abbreviation and misspelling rates, carrier mix. Only these aggregates leave the profiler.
2. **Phrase grammar** per category from the taxonomy ("DET {qty}HRS @{rate}", "LUMPER {amt}", "TONU", "{amt} PD ON INV {inv}"). Gold items and offsets are known **by construction**.
3. **Noise injection**: carrier-style abbreviations, misspellings, casing, run-on text. Optional local-LLM paraphrase applies to templates only, never to real notes, and gold is re-derived afterwards.
4. **Fake identities**: Faker names, phone numbers and invoice ids, plus fictional carrier names. Real carrier names are excluded.

## 9.3 Quality of the simulated dataset

A synthetic set is published only if it passes all four checks. Results are stored with the set and shown in the D5 report.

| Dimension | Check | Pass rule (default) |
|---|---|---|
| **Fidelity** | Jensen–Shannon distance between synthetic and real distributions (category mix, items per note, log-amount, note length, abbreviation rate); KS test on log-amounts | JSD ≤ 0.10 per marginal |
| **Privacy** | Longest common substring and 8-gram overlap with every real note; no real names, phones or invoice ids; nearest-neighbour distance not smaller than real-to-real | No 8-gram shared with any real note except taxonomy vocabulary; zero real identifiers |
| **Validity** | Rules-only itemizer re-derives the gold for every note; two team members spot-check 50 notes blind | 100% rule re-derivation; spot-check agreement ≥ 95% |
| **Utility** | Rank correlation between per-category accuracy on SYNTH and on DEV for the same build; accuracy gap | Spearman ρ ≥ 0.6; gap reported, never hidden |

Synthetic results are always labelled **synthetic** and never mixed into the TEST, DEV or FRESH numbers that answer the client's accuracy target (Jordon et al., 2022).
