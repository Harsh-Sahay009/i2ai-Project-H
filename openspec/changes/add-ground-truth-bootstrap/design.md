## Context

C4 container **Ground Truth Bootstrap** (Dataset Profiler, Split Builder, Taxonomy Drafter, Labelling Pack Builder, Label Validator & Sealer). Placement: **common core** for the labelling protocol and split rules; seed and shares are **configurable layer** (`split.*`). Position: **owned**.

Authority: the tool drafts D1 and prepares D2. The client owner approves D1, and people write the TEST and VALIDATION labels.

## Goals / Non-Goals

**Goals:** D1 approved and TEST sealed in time for D3; no tool output in any TEST or VALIDATION label; every step repeatable from the seed.

**Non-Goals:** long-term storage (add-ground-truth-store); UI labelling (add-web-ui); writing labels on anyone's behalf.

## Decisions

- **Standalone CLI.** `itemizer gt profile | split | draft-taxonomy | approval-doc | record-approval | label-packs | import-labels | agreement | client-pack | import-client | seal`. It has no dependency on the foundation changes because they are not built yet.
- **Split by distinct note** (ADR 0012). The file's 729 notes form only 173 formats, and the largest has 98 notes, so keeping each format in one set could leave TRAIN without the most common format. Formats may cross sets, and each TEST note records whether its format appears in TRAIN.
- **Source file.** Every partition comes from `AutoPay Dispute Data 20220815_withExamples.xlsx`, kept out of Git. Its example sheet holds the team's hand-labelled notes, which go to TRAIN.
- **Order.** Profile, then split, then draft the taxonomy from TRAIN only, then label. TEST and VALIDATION notes never shape the categories.
- **Provisional strata.** Before labelling: `large` when the disputed amount is at or above `strata.large_dispute_usd` ($180, the top decile), `multi` when the note has two or more money tokens outside a rate × quantity pattern, otherwise `single`. A money token needs a dollar sign or two decimals, because notes also hold dates, times, weights and bill numbers. That gives 536 single, 94 multi and 99 large notes. TEST takes 100 / 50 / 50. After labelling, the stratum comes from the gold items. If the final mix misses 100/100 by more than `split.max_stratum_gap_notes`, the tool lists replacements from the reserve.
- **Reserve.** `split.test_reserve_notes` extra notes are drawn with TEST and left untouched. Unused ones join TRAIN and VALIDATION after sealing, so no note is wasted and nothing leaks.
- **Taxonomy draft.** The LLM receives a sample of TRAIN notes and returns categories with definitions, includes, excludes and examples. Every quote is checked as verbatim, and failures are dropped. The call goes straight to the provider because the router does not exist yet; it refuses to run unless the dataset is `open_anonymized`, and it records the model id and prompt hash. Without `--send`, the command only writes the prompt. `--proposal-file` loads a draft written elsewhere and checks it the same way.
- **Notes read while drafting** are recorded and can never enter TEST or RESERVE, so a re-split cannot leak them. Notes quoted as D1 examples stay in TRAIN.
- **Name scan by pattern.** Notes are upper case, which defeats a named-entity model, so the scan uses cue words such as `DRIVER`, `PER` and `FROM PPG`. It finds some names, not all.
- **No note text in Git.** `taxonomy/categories.yaml` holds fingerprints and offsets. The approval document holds real quotes and stays out of Git.
- **Excel for labelling.** The UI will not exist in time. Each workbook has the note, carrier and disputed amount, with item rows for category (dropdown), amount, evidence quote and derivation, plus a "no charge stated" flag. Each labeller gets a separate file.
- **Blind by construction.** The pack builder has no input for predictions or suggestions on TEST and VALIDATION packs. A test inspects every generated file.
- **Labelling rules in every pack.** Notes state the amount in several ways, so the rules are written out. A balance due with no other amount for that charge is the item. A balance due beside listed charges is a total, and the row may be flagged. One amount for several charges uses `combined_charges`. `@$300` beside days is a stated total unless the note gives no total. Spaces can separate thousands.
- **Who labels what.** 50 notes by two people; 150 notes by one person, with a spot check of 15 by a second person; all 50 double-labelled notes reviewed by Jake or a PPG accountant, whose decision becomes the gold label.
- **Agreement.** Cohen's kappa on category for matched items, exact match on amounts, item count match. Low agreement means the definitions are unclear, so the fix is to the definitions before sealing.
- **TRAIN assist.** TRAIN labels may start from LLM suggestions, recorded as such. VALIDATION labels may not, because thresholds are fitted on them.
- **Versions and telemetry.** Versioned outputs: dataset profile, scan report, split manifest, taxonomy draft, approval record, label files, agreement report, sealed TEST. The episode store does not exist yet, so each command appends who, when, input hashes and output hashes to a JSONL log that is imported later.

## Schedule

This assumes Jake answers within a day. Nothing is built yet, so it has no slack.

| When | Work | Who |
|---|---|---|
| 2 Nov | Build and run profile, split and taxonomy draft; edit the draft; send D1 to Jake | Team |
| 3 Nov | Approve D1; build labelling packs and validator; start labelling | Jake, team |
| 3–4 Nov | Label 200 TEST notes (the scope estimates 2 to 3 hours); label at least 100 VALIDATION notes and enough TRAIN notes for few-shot examples | Team |
| 4 Nov | Review the 50 double-labelled notes; resolve disagreements; seal TEST | Jake or a PPG accountant, team |
| 5 Nov | Level 1 gate on TEST; show Jake the prototype (D3) | Team, Jake |

## Risks / Trade-offs

- [Jake is slow to approve D1] → label against the draft, mark those labels provisional, and remap through the version mapping if the list changes.
- [Rushed labels] → the validator rejects non-verbatim evidence and bad amounts; the agreement report shows weak definitions before sealing.
- [Pressure to pre-fill TEST labels to save time] → not supported by design. The scope's estimate of 2 to 3 hours makes it unnecessary.
- [The notes hold names and emails, though the file is public] → the scan reports them, external sends stay blocked until the operator records a decision, and the D1 document quotes around them.
- [The dataset differs from the scope's figures] → the profile shows both side by side, and D5 reports the dataset actually used.
- [A small LLM sample misses rare categories] → `other_unmapped` catches them; the catch-all share is measured as error (c).

## Open Questions

- The public link for the file (ADR 0013).
- Which two team members label, and whether Jake or a PPG accountant does the review.
