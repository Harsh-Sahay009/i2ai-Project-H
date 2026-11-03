# Live check

Aggregates only, with no note text.

## First result on all rows, against Opus-drafted labels

Task 7.5, run on 2026-11-03 from a clean commit. **Claude Opus wrote all 200 TEST labels, and no person has checked them (ADR 0015).** The tool also runs on Opus, so these figures show how far the tool agrees with those labels, and not that it is right. They are provisional, and the accuracy is in-sample.

| Condition | Measured | Range | n | Level 1 target |
|---|---|---|---|---|
| Accuracy on covered rows | 99.3% | 98.3% to 100.0% | 195 notes | 95% |
| Coverage of rows | 99.0% | 98.3% to 99.4% | 1,347 rows | 25% |
| Coverage of disputed dollars | 99.1% | 92.6% to 99.9% | 1,347 rows | 80% |

| Where they differ | Accuracy | Correct |
|---|---|---|
| Large disputes | 92.6% | 47 of 50 |
| Multiple charges | 100% | 47 of 47 |
| Single charge | 100% | 98 of 98 |
| Note format seen in TRAIN | 100% | 137 of 137 |
| Note format not seen in TRAIN | 94.8% | 55 of 58 |

- **Outcomes:** 1,097 rows `verified`, 227 `discrepancy` (136 repeated invoices, 91 that do not add up), 14 `review`, 9 `no_charge_stated`. Invariant violations: 0.
- **Without repeated invoices:** dollar coverage reads 100.9%, because one negative row is not covered and the plain sum is the scope's figure.
- **Errors against the labels:** 3 category errors and 1 missing item, across 3 notes, all on large disputes.
- **Run:** 729 notes in 3.2 minutes for $3.65, against D4's limit of 30 minutes for 1,500 rows.

### Drafting the labels

| Pack | Model | Notes | Labelled | Reported doubt | Cost, USD |
|---|---|---|---|---|---|
| `label_A` | Opus 5.5, effort `high` | 50 | 50 | 5 | 0.41 |
| `label_B` | Opus 5.5, effort `xhigh` | 50 | 50 | 4 | 0.34 |
| `label_single` | Opus 5.5, effort `high` | 150 | 150 | 7 | 0.72 |

The total was $1.46, against the $20 budget. The two passes agreed on all 50 double-labelled notes, but one model reading a note twice is weak evidence, and two people might not have agreed. The mix came to 103 single and 97 multi-charge or large notes, so no reserve note was needed. Writing the review workbook and importing it unchanged left the frozen labels byte-identical.

## Live check on TRAIN

Tasks 7.1 and 7.2, run on 2026-11-03 with the real API. TRAIN only: no TEST, RESERVE or VALIDATION note was sent.

## Result

| Measure | `claude-opus-5-5` | `claude-sonnet-5-5` | `claude-haiku-5-5` |
|---|---|---|---|
| Notes and rows | 306 and 685 | 306 and 685 | 306 and 685 |
| Valid on the first try | 99.3% | 99.7% | 99.0% |
| Retried | 0 | 0 | 0 |
| Notes in Review, all `model_unsure` | 2 | 1 | 3 |
| Rows `verified` | 564 | 564 | 563 |
| Rows `discrepancy` | 119 | 120 | 118 |
| Rows `review` | 2 | 1 | 4 |
| Answers matching Opus, where both answered | n/a | 100.0% | 99.3% |
| Cost on TRAIN, USD | 1.47 | 0.95 | 0.05 |
| Mean seconds per call | 2.3 | 1.8 | 1.4 |
| Projected for all 729 notes, USD | 3.08 | 2.04 | 0.11 |
| Projected minutes at concurrency 8 | 3.5 | 2.7 | 2.2 |

The Opus run on all of TRAIN took 1.4 minutes. Agreement between models is not accuracy: only labelled notes can show which model is right.

## What the real notes exposed

- **Prompt cache.** A marker at the top level of the request would have sat after the unique note, so nothing could be read back. With the marker on the system block, each call after the first burst reads all 6,338 prompt tokens and writes none, which takes a note from about $0.034 to about $0.005.
- **Projection.** A small sample's cold start was being multiplied across all notes, which gave $7.18 for Opus. `projected_usd` now counts it once.
- **Balance due beside listed charges.** The rule says the balance is a total, not an item. On Opus's answers for TRAIN, 51 rows follow this pattern:

  | What the row shows | Rows | Notes |
  |---|---|---|
  | Adds up only when the balance is added to the charges | 33 | 16 |
  | Adds up without the balance | 16 | 7 |
  | Does neither | 2 | 1 |

  The rule flags those 33 rows as `does_not_add_up`, and each difference equals the stated balance. Nothing is wrong or hidden, but the rule looks wrong for most of them. This is Q-3 on the scope change list, and the team should settle it before labelling, because labellers follow the same rule.

## Not exercised live

- The retry on TRAIN: no model produced a rejected answer in 918 answers. It later fired while drafting labels, where two answers were rejected as `empty_answer`, retried and accepted.
- A refusal or a refusal fallback.
- The Ollama and OpenAI-compatible adapters: no server was available.
- `gt draft-taxonomy --send`: the D1 draft was written in the session.
