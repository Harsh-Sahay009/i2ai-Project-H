# 12. Separate train, validation and test sets from one file

Date: 2026-11-02

## Status

Accepted. Amends [4. "Training Algorithm" means calibration and configuration tuning, not weight training](0004-tuning-not-training.md) and [5. KPIs are computed only from immutable versioned inputs](0005-kpis-from-versioned-inputs.md). Replaces the DEV set with TRAIN and VALIDATION.

## Context

The architecture had TEST and FRESH but one DEV set doing three jobs: writing the lexicon and few-shot examples, fitting calibration and thresholds, and judging candidate changes. A change could be judged on the same notes it was built from.

To guard against that, the promotion gate evaluated every candidate on TEST, up to 5 times per milestone. Choosing between candidates on TEST results is tuning, even with aggregates only, and the scope says the test set "is never used to tune the tool".

The team has also decided that every partition comes from one file (ADR 0013). That file has 1,347 rows, 729 distinct notes and 9 rows with no note. 636 notes appear once, and the top 10 notes cover 423 rows. Dollars are concentrated: the largest 10% of rows hold about 70% of the disputed dollars.

## Decision

| Set | Used for | Who writes the labels | Row-level reading by the team |
|---|---|---|---|
| **TRAIN** | Lexicon, few-shot examples, prompts, rules, case mining | People; may start from model suggestions, recorded as such | Yes |
| **VALIDATION** | Calibration, thresholds, comparing candidates, promotion gate | People, without seeing tool output | Aggregates only |
| **TEST** (D2) | Level gates at D3 and D4 only; never used to choose between candidates | People, without seeing tool output | Aggregates only until the final freeze |
| **FRESH** | Not expected, since all data comes from one file; defined in case a new month arrives | People, without seeing tool output | Aggregates only until the final freeze |

Rules:

- **Split by distinct note.** A normalized note belongs to exactly one set, so a repeated note can never appear in two sets.
- **Repeated formats may cross sets.** Notes that differ only in their numbers can land in different sets, because future exports will also repeat known formats with new numbers.
- **Report accuracy both ways.** Each TEST note records whether its format appears in TRAIN, and accuracy is reported for seen and unseen formats.
- **Draw TEST first:** 100 single-charge, 50 multi-charge and 50 large-dispute notes, stratified by how often each note repeats. Large means at or above `strata.large_dispute_usd`. TEST over-samples large disputes on purpose, and weighting back to the real mix corrects for it.
- **Reserve.** `split.test_reserve_notes` (20) extra notes replace TEST notes if the labelled mix is off. After sealing, unused reserve notes join TRAIN and VALIDATION. Nobody has seen them, so nothing leaks.
- **Already-labelled notes go to TRAIN.** The notes in the team's example sheet have been read and labelled by hand, and notes quoted as D1 examples are visible to everyone, so they stay in TRAIN.
- **Notes read while drafting D1 never enter TEST.** They can go to TRAIN or VALIDATION. Keeping them all in TRAIN would leave VALIDATION with almost no multi-charge notes, because the file has only 94.
- **Divide the rest** into TRAIN and VALIDATION using `split.validation_share`, with the same stratification.
- **Provisional strata.** Before labelling, the stratum comes from the money tokens in the note and the disputed amount. After labelling, it comes from the gold items.
- **Record** the seed and the assignment of every note in a versioned split manifest, and check disjointness whenever a set or few-shot version is published.
- **Development runs use TRAIN and VALIDATION only.** A run on the whole file happens only at a Level gate, after TEST is sealed.
- **Where each number comes from.** Accuracy comes from TEST. Coverage comes from the run on all rows, which needs no labels.
- **Promotion uses VALIDATION only.** The gate refuses any TEST request from the Training & Calibration Pipeline.
- **TEST budget.** `kpi.test_peek_budget_per_milestone` defaults to 1. Every TEST evaluation is logged and the count is reported in D5.
- SYNTH and ADV stay outside the split.

The split at seed 20261102, using provisional strata (536 single, 94 multi and 99 large notes in the file):

| Set | Notes | Rows | Disputed $ | Single / multi / large |
|---|---|---|---|---|
| TEST | 200 | 307 | 72,237 | 100 / 50 / 50 |
| TRAIN | 306 | 685 | 89,146 | 251 / 28 / 27 |
| VALIDATION | 203 | 324 | 22,176 | 175 / 15 / 13 |
| RESERVE, released after sealing | 20 | 22 | 4,446 | 10 / 1 / 9 |

Of the 200 TEST notes, 138 have a format that appears in TRAIN and 62 do not. Dollars by set vary with the seed, because a few rows are very large.

Alternatives considered:

- **Keep each format (notes that differ only in numbers) in one set.** Rejected after simulation. The 729 notes form only 173 formats, and the largest has 98 notes. Across 300 seeds, the largest format landed entirely in TEST 35% of the time, so the tool would never train on the most common format, and TEST varied from 274 to 660 rows.
- **Split by date.** Rejected. 73% of rows fall in June and July 2022, and August has only 40 rows with 8 notes that appear in no earlier month.

## Consequences

- TEST numbers stay meaningful because no candidate is ever chosen on them.
- Because all sets come from one file, every accuracy number is labelled in-sample.
- If a Level gate fails on TEST and the team fixes the tool and evaluates again, that is a second look at TEST. It uses budget and is reported in D5.
- More notes need labels, and VALIDATION labelling must be blind. `add-ground-truth-bootstrap` covers this work.
- Replay diffs at row level are available on TRAIN and replay packs only. VALIDATION shows error-type changes as aggregates, which is slower to debug but keeps VALIDATION usable.
