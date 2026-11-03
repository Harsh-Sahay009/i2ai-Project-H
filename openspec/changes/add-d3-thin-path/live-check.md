# Live check on TRAIN

Tasks 7.1 and 7.2, run on 2026-11-03 with the real API. TRAIN only: no TEST, RESERVE or VALIDATION note was sent. Aggregates only, with no note text.

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

- The retry after a rejected answer: no model produced a rejected answer in 918 answers. Unit tests cover it.
- A refusal or a refusal fallback.
- The Ollama and OpenAI-compatible adapters: no server was available.
- `gt draft-taxonomy --send`: the D1 draft was written in the session.
