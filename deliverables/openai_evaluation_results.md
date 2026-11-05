# Separate OpenAI evaluation — 5 November 2026

A separate GPT-5.4 Mini benchmark completed on all 200 received reference notes. The user authorized **$5 total** across development, benchmark, full corpus and resumptions. The same-model full-corpus run has now completed all 729 distinct notes and 1,347 dispute rows.

| Completed benchmark measure | Result |
| --- | ---: |
| Exact agreement on answered notes | 189/197 = 95.94% |
| 95% Wilson interval | 92.19%–97.93% |
| Strict yield including abstentions | 189/200 = 94.50% |
| Reference-stratum row-weighted agreement | 96.41% |
| Weighted bootstrap interval | 93.15%–98.80% |
| Benchmark row coverage | 304/307 = 99.02% |
| Benchmark dollar coverage | $70,402.13/$70,577.40 = 99.75% |
| Benchmark rows accepted without reading | 241/307 = 78.50% |
| Verifiable extracted items | 277/277; zero invariant violations |
| Reported usage including development check | $0.319206 |
| Benchmark processing time | 433.67 seconds (7.23 minutes) |

The result clears the user's >90% target. Answered-note and weighted agreement exceed 95%, while strict yield is below 95%; do not interchange these denominators or claim statistical assurance of a 95% accuracy floor. The answered-note 95% Wilson lower bound is 92.19%.

## Quality limits and comparison

Eight answered notes differ from the references; three notes are abstentions. Item-level differences: four category errors, three amount errors, one missing item and one extra item. Large-dispute row-weighted agreement is 85.29% (43/50 exact note matches); unseen-format agreement is 48/54 = 88.89%. These are review priorities even though overall performance clears 90%. The private review file contains all eleven disagreement/abstention cases.

The original labels retain source `model_draft`, and their bytes are unchanged. Harsh confirmed in chat that he reviewed all 200 reference labels; this provenance is stored separately with hashes. We have not fabricated per-item human adjudications or corrected labels. Interpret these figures as exact agreement against that user-reviewed reference set, not evidence that every item in the full corpus is correct.

The high-value note with $400 already paid and $8,000 outstanding is **incorrectly extracted by OpenAI**: its prediction contains only a $400 `other_unmapped` charge and omits the $8,000 balance. The note maps to two $8,000 dispute rows. Those rows count as covered discrepancies, which increases dollar coverage while leaving this $16,000 exposure unresolved. Do not interpret the higher dollar-coverage metric as resolution of this case or as higher correctness. Keep both rows in manual review; preserve the separate reference-derived human-assisted candidate.

The agreement metric matches item categories and amounts within $0.01. It does not independently measure every semantic field such as paid-versus-charge line type. Verbatim evidence/invariant checks are necessary but do not establish correct interpretation.

Gemini's completed benchmark was 196/198 = 98.99% answered-note agreement and 196/200 = 98.00% strict yield. OpenAI is lower on agreement but higher on benchmark dollar coverage (99.75% versus 77.33%). No responses are mixed across models. Benchmark coverage includes explicit discrepancies, not just automatic acceptance. Historical Alejandro-weighted metrics use a different population and are not directly comparable to this benchmark-weighted metric.

## Cost and reproducibility

- Pinned snapshot: `gpt-5.4-mini-2026-03-17`, medium reasoning; temperature omitted; max completion tokens 16,000; standard service tier; `store=false`.
- Official rates checked: input $0.75/M, cached input $0.075/M, output $4.50/M. [OpenAI model documentation](https://developers.openai.com/api/docs/models/gpt-5.4-mini).
- Shared private ledger: `data/evaluation/openai_spending.json`. Before each request a $0.372 conservative maximum is durably reserved (full 400,000-token context charge plus requested maximum output charge). Metered responses settle to actual token cost; unmetered failures retain reservations. The total guard can stop below $5 and does not control unrelated account activity or taxes.
- Development request used a note outside the benchmark. Benchmark model, prompt, taxonomy, schema and references were fixed before scoring; no partial scores guided changes. Full corpus reuses this candidate's cache and the same ledger.
- New worktree: `/Users/harshsahay/.codex/workspaces/i2ai-Project-H-openai`, branch `codex/openai-evaluation`; commands require `PYTHONPATH=src` while reusing the original environment.
- 243 relevant tests passed; an independent code review found no remaining blocker. The original Gemini checkout still matches its frozen protocol.
- The credential was saved only in ignored `.env` with mode 0600. No credentials, source notes, workbook, raw predictions or cache are tracked by Git.

## Completed full-export result

| Full-export measure | Result |
| --- | ---: |
| Distinct notes processed | 729/729 |
| Source dispute rows | 1,347/1,347 |
| Notes with an accepted extraction result | 719/729; 10 model-unsure notes |
| Row coverage | 1,336/1,347 = 99.18% |
| Dollar coverage | $184,839.94/$186,345.02 = 99.19% |
| Rows accepted without reading | 1,096/1,347 = 81.37% |
| Dollars accepted without reading | $92,379.39/$186,345.02 = 49.57% |
| Row outcomes | 1,084 verified; 12 no-charge; 240 discrepancy; 11 review |
| Verifiable extracted items | 879/879; zero invariant violations |
| Total reported usage, all phases | $1.05022950 of $5 authorized |
| Generation requests, all phases | 737, including eight validation retries |
| Unknown/unsettled cost reservations | $0 |
| Full-data sweep processing time | 1,063.21 seconds (17.72 minutes), reusing prior cache |

The eleven uncovered rows total $1,505.08. The 240 discrepancy rows account for $92,460.55; they are covered in the extraction metric but remain exceptions. Together 251 discrepancy/review rows across 167 distinct notes require attention. Private artifacts include `all/manual_review_queue.json` and `all/abstention_review.md`. The benchmark's eleven disagreement/abstention cases remain separately listed.

Only 200 notes have the supplied, user-reviewed reference labels. Processing all 729 establishes full-export coverage; it does not measure accuracy against human labels on the other 529 notes. The all-scope summary also computes a 98.08% weighted approximation using the full corpus's predicted stratum mix; its weighting differs from the fixed benchmark's 96.41%. Use the fixed benchmark result for the direct model comparison and do not present 98.08% as directly verified accuracy on all 729 notes.

All benchmark predictions were identical when reused in the full sweep. Dataset, references, prompt, taxonomy, settings and source hashes remain pinned. No provider or quota failures occurred in this candidate's generation requests, and there are no automatic retries running.

The candidate clears the user's overall >90% benchmark target, but does not meet a 95% strict-yield requirement and shows material large-dispute weaknesses. Retain it as an evaluated candidate with review of exceptions; do not treat the successful run, high coverage or zero invariant violations as authorization for automatic settlement. Official D3 acceptance remains unassessed. The OpenAI worktree and branch are retained separately to preserve the original Gemini frozen source; these new changes have not been pushed.
