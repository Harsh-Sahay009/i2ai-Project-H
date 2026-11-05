# Separate free Flash-Lite benchmark — 5 November 2026

Gemini 3.5 Flash-Lite completed inference for all 200 received benchmark notes. It exactly matched Alejandro's model-drafted references on 196 of 198 answered notes. Two notes were abstentions. Harsh subsequently confirmed in chat that he verified all 200 reference labels and accepted the accuracy result. The benchmark therefore has user-confirmed human review and exceeds the requested >90% and project 95% numerical targets. Official D3 acceptance remains unassessed.

| Measure | Result |
| --- | ---: |
| Exact note agreement among answered notes | 196/198 = 98.99% |
| 95% Wilson interval for note agreement | 96.39%–99.72% |
| Strict yield, counting abstentions unsuccessful | 196/200 = 98.00% |
| Answered-note share | 198/200 = 99.00% |
| Reference-stratum row-weighted agreement | 98.99% |
| Weighted bootstrap interval | 97.18%–100.00% |
| Benchmark row coverage | 304/307 = 99.02% |
| Benchmark dollar coverage | $54,577.40/$70,577.40 = 77.33% |
| Rows accepted without reading | 248/307 = 80.78% |
| Valid/verifiable extracted items | 277/277; zero invariant violations |

Exact agreement requires the same item categories and amounts within $0.01; item order does not matter. The two mismatched notes contain three category differences, all predicted as `other_unmapped`. There are zero amount errors, missing items or extra items among answered notes. Both mismatches are in the large-dispute stratum. Its row-weighted agreement is 95.45%; small subgroup uncertainty remains material.

## Human review confirmation

On 5 November 2026, Harsh stated that he had verified accuracy and, when asked whether he checked all 200 reference labels or only the four flagged cases, answered “all.” This is recorded as user-confirmed review of all 200 labels. The confirmation is linked to the exact reference and result hashes in private `human_review_confirmation.json`. No corrected label file or per-item adjudications were supplied; the original model-draft labels, inference results and computed scores remain unchanged. The 98.99% answered-note result and 98.00% strict yield are reported with this review provenance.

## Dollar coverage needs attention

One abstention is a zero-dollar note. The other corresponds to two $8,000 rows, accounting for the entire $16,000 uncovered amount. Benchmark row coverage is high while dollar coverage is 77.33%, below 90%. Removing repeated rows gives 100% dollar coverage under the current duplicate policy; that does not remove the need to inspect the original $16,000 exposure and duplicate treatment. Do not present the deduplicated figure alone.

Of 307 rows, 246 were verified, 56 were discrepancies, 2 stated no charge, and 3 require review. Covered rows include explicit discrepancies; coverage is not automatic acceptance. Only 80.78% of benchmark rows and 43.91% of benchmark dollars were accepted without reading.

## Reproducibility and interruptions

- Fixed experiment: `data/evaluation/gemini-lite-v1/benchmark/`; separate cache; medium effort; temperature 0; five-second request interval.
- All 200 references have source `model_draft`; reference contents were unchanged. No benchmark score was inspected before the complete run, and no settings were tuned against partial results.
- First pass saved 56 responses before a provider interruption. One diagnostic request recovered the first unanswered note; the resumed pass reused cached responses and finished all 200. Subsequent transport diagnostics recorded HTTP 503 service errors. The first interruption's exact code was not retained.
- Processing time: first pass 325.13 seconds plus resumed pass 839.97 seconds (19.42 minutes), excluding diagnostic/cooldown time. Cached processing time is included; this is not a fresh-run speed comparison.
- Free-tier model configuration used; no paid billing enabled and no local model downloaded. Zero configured API cost is not an independent billing audit.
- Protocol pins dataset, references, rendered prompt, taxonomy, settings, model and code hashes. The completed result contains no provider-unavailable or budget-exhausted notes.
- This measures 200 notes mapping to 307 rows, not all 729 distinct notes/1,347 rows. The weighted population is the benchmark's reference strata, so its weighted score is not directly comparable to Alejandro's historical 99.3% full-population-weighted figure.

## Next work

1. Full-benchmark human review is user-confirmed. Preserve that confirmation alongside the original drafts; if corrections or individual decisions are supplied later, record them separately and recompute affected scores.
2. Measure full-export coverage using the same candidate. The 200 cached benchmark notes leave 529 new notes; the account's 500-request daily limit means the remainder needs multiple quota days after today's usage. Preserve one model and one protocol; do not fill gaps with another model.
3. Keep D3 acceptance unassessed until full-export coverage and the required project records are checked.

Raw notes, predictions, credentials and the human-review sheet remain in ignored private files. No results have been pushed to GitHub.
