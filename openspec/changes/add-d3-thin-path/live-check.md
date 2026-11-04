# Live check

Aggregates only, with no note text.

## First result on all rows, against Opus-drafted labels

Task 7.5, run on 2026-11-03 from a clean commit. **Claude Opus wrote all 200 TEST labels, and no person has checked them (ADR 0015).** The tool also runs on Opus, so these figures show how far the tool agrees with those labels, and not that it is right. They are provisional, and the accuracy is in-sample.

| Condition | Measured | Range | n | Level 1 target |
|---|---|---|---|---|
| Accuracy on covered rows | 99.3% | 98.3% to 100.0% | 195 notes | 95% |
| Coverage of rows | 99.0% | 98.3% to 99.4% | 1,347 rows | 25% |
| Coverage of disputed dollars | 99.1% | 92.6% to 99.9% | 1,347 rows | 80% |

Coverage also counts rows flagged for an accountant to read. What an accountant can accept without reading the note is **82.1% of rows and 50.0% of dollars**. Level 2's numbers are met too. Level 3 reads `work_not_built`, because its code list and cost-driver summary do not exist.

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

Across all 881 items, 15 are taxes and 1 is an amount already paid, and none use rate × quantity. That path does work on a real model: an invented note, "3 HOURS @ $40 PER HOUR", came back as 120.00 with `rate_x_quantity`. So zero on this file more likely means its notes do not need it, though only a person reading them can confirm that.

### Kimi K3, against the same Opus labels

Run on 2026-11-04 at the team's request, on all rows, with the same prompt and worked examples. It went through `--extra-peek`, so the TEST ledger now reads 2 runs against a budget of 1, with the reason. The status page still reports the Opus run. **TEST does not choose between models, and neither set of labels has been checked by a person.**

| Measure | `claude-opus-5-5` | `kimi-k3` |
|---|---|---|
| Accuracy, weighted | 99.3% | 99.3% |
| Correct of covered TEST notes | 192 of 195 | 196 of 199 |
| Large disputes | 47 of 50 | 47 of 50 |
| Multiple charges | 47 of 47 | 47 of 47 |
| Single charge | 98 of 98 | 102 of 102 |
| Coverage, rows and dollars | 99.0% and 99.1% | 99.8% and 99.9% |
| Accepted without reading, rows and dollars | 82.1% and 50.0% | 82.4% and 50.4% |
| Notes the model was unsure about | 10 | 3 |
| Answers rejected, then fixed on the retry | 0 | 2 |
| Run on all rows | 3.2 minutes | 16.8 minutes |
| Mean seconds per note | 2.1 | 11.1 |
| Cost | $3.65 | $4.54 computed, $3.91 by the fall in Moonshot's balance |

The two models gave the same categories and amounts on 717 of the 718 notes both answered. That is more than Opus agreeing with itself, but they share a prompt and its rules, so a mistake in those rules would not show. Kimi's cost is an estimate, because Moonshot's price table would not load, and the balance suggests the listed rates run about 16% high.

### Rehearsal for the 5 November meeting

Run on 2026-11-03 from a clean commit, on the real data, driving the local page in a real Chrome with a throwaway profile.

| Check | Result |
|---|---|
| Run and score from a clean commit | No model calls, and the budget event is `rescored`, with no second-peek warning. It first failed: the morning's ledger line was not recognised, and that is fixed |
| Upload the AutoPay file with model calls blocked by a dead proxy | Finished in 2.6 seconds with no new answers, and the workbook hash matches the command line's |
| Chrome's `Origin` on each `POST` | Local, so the page accepted them. Another site's `Origin`, a missing one, and another site's `Host` are refused by the running server |
| Open the workbooks in real Excel, by script | Both open with no repair prompt. `Items` has 1,520 lines and `Row Summary` 1,348, as expected. No person has looked at them yet |
| Upload an invented file through the real API | 6 notes, 6.5 seconds, $0.22. The pre-check first said $0.03, because it left out the cold start. It now says $0.22 |
| Correct one label on a copy of the data, score, then undo | Accuracy went from 99.3% to 98.8% and back, with no model calls and no budget |

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

- A person looking at the page or the workbook: the checks above were driven by script.
- The retry on TRAIN: no model produced a rejected answer in 918 answers. It later fired while drafting labels, where two answers were rejected as `empty_answer`, retried and accepted.
- A refusal or a refusal fallback.
- The Ollama adapter: no server was available. The OpenAI-compatible adapter has since run against Moonshot, which found a defect: it sent a temperature that Kimi K3 refuses.
- `gt draft-taxonomy --send`: the D1 draft was written in the session.
