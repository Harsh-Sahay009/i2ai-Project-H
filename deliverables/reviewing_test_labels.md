# Reviewing the TEST labels and running the test again

Claude Opus wrote the 200 TEST labels (ADR 0015). The tool also runs on Claude, so until people have checked them, the accuracy figure shows how far the tool agrees with those labels, and not that it is right. This file explains how to check and correct the labels, and how to get a new result.

The labels live under `data/`, which Git ignores. Do not copy notes or labels into a tracked file: this repo is public.

## Rules while reviewing

1. **Do not open `data/runs/` or any `itemized.xlsx` while reviewing.** Those hold the tool's answers. A reviewer who has seen them may follow them, which defeats the review. The review workbook holds no tool output.
2. **Read the note first, then the label.** Ask what the note says, and then whether the label says the same.
3. **Follow the labelling rules** on the workbook's `Instructions` sheet. Never change an amount to make a row add up.
4. **If you saw the tool's answers at the meeting, judge from the note anyway.** The workbook already shows Opus's label, and the tool agrees with it on almost every note, so the few notes where they differ are the ones to read most carefully.

## Step 1: write the review workbook

```bash
itemizer gt label-review-pack
```

This writes `data/bootstrap/packs/test_label_review.xlsx`, with the current label of every TEST note. Run it again after each import, so that it shows the latest labels.

## Step 2: go through the `Labels` sheet

Notes come with the ones most in need of a person first, and `priority` says why:

| `priority` | Meaning |
|---|---|
| `labellers_disagreed` | The two Opus passes differ. Labeller A's answer is the one shown |
| `model_doubt:<reason>` | Opus was not sure, and gave its best reading |
| `large_dispute` | The dispute is $180 or more, so an error matters more |
| `several_charges` | The label has two or more charges |
| `no_charge_stated` | The label says the note states no charge |
| `already_checked` | A person has checked this note already |

For each note, do one of these:

| The label is | What to do |
|---|---|
| Right | Put `Y` in `checked` on any of the note's lines |
| Wrong on a charge | Change `category`, `amount`, `evidence`, `line_type` or `derivation` on that line |
| Missing a charge | Fill in the blank line under the note. For another, copy a line and keep its `note_id` |
| Listing something that is not a charge | Clear that line's `category`, `amount`, `evidence`, `line_type` and `derivation` |
| Wrong, and the note states no charge | Clear the item lines, and put `Y` in `no_charge_stated` on the note's first line |

A changed label counts as checked, even if you forget the `Y`. You do not have to finish in one sitting: notes you leave alone stay as they are.

If you split the work, have each person take a different range of notes, because the last import of a note wins.

## Step 3: import the workbook

```bash
itemizer gt import-label-review data/bootstrap/packs/test_label_review.xlsx --reviewer "<your name>" --date <YYYY-MM-DD>
```

If any line fails a check, for example an amount that is not in the evidence, the whole file is rejected and no label changes. The failures are listed by row in `data/bootstrap/labels/test_label_review.errors.csv`. Fix them and import again.

## Step 4: run the test again

What to do depends on what changed:

| What changed | What to run | Model calls | TEST budget |
|---|---|---|---|
| Only labels | `itemizer evaluate`, then `itemizer acceptance d3` | None | Free, because the run is the same |
| A category renamed or merged (see below), or the category list, worked examples, prompt or grammar, or `reconcile`, `review`, `kpi` or `gates` in `config/run.yaml` | `itemizer run`, then `itemizer evaluate --extra-peek "<reason>"`, then `itemizer acceptance d3` | Yes | Past the budget, so the reason is logged and flagged on the page |
| Code that changes what the tool answers | The same as the row above | Yes | Past the budget |

`itemizer evaluate` on an out-of-date run stops and says what changed, and nothing is charged. The result is at `data/reports/d3_summary.html`.

Each extra peek is a chance to pick the best-looking score, so use them rarely. Correcting labels after seeing a result is allowed, but the page counts corrections made after the freeze. Do not change a label because the tool answered differently: change it only because the note says so.

## If a category is renamed or merged

This can happen when the team edits D1, or when the client asks for a change at approval. **Do not use find-and-replace in the workbook.** It would mark every label it touches as `person_corrected`, as though someone had read those notes, and the final seal's check on unread drafts would then pass. The review workbook and its import refuse to run while labels hold an old code, for this reason. Use:

```bash
itemizer gt rename-category <old> <new>
itemizer gt rename-category <old> <existing> --merge
```

This changes the code in the category list, the worked examples and every stored label. Each label keeps who wrote it, and it does not count as a correction. To change a category's name or definition, edit `taxonomy/categories.yaml` directly, and leave its code alone.

Then follow the row for category changes in Step 4. A split, where one category becomes two, needs a person to choose for each note, so add the new category to the list and correct those labels in the workbook.

## If the balance-due rule changes

The current rule says a balance due beside listed charges is a total, and not an item. If the team and Jake choose another rule (Q-3 on the scope page):

1. Change the rule in `INSTRUCTIONS` in `src/itemizer/bootstrap/labels.py` and in `prompts/itemize_v1.md`.
2. Correct the affected labels using the steps above. Search the workbook's `note` column for `BALANCE DUE`.
3. Follow the second row of the table in Step 4.

## Making the labels final

Results stay provisional, and D3 stays `open`, until all of these are done:

1. Every draft has been checked. The status page shows how many remain.
2. The client reviews the 50 double-labelled notes:

   ```bash
   itemizer gt client-pack
   # the client fills in the workbook
   itemizer gt import-client data/bootstrap/packs/client_review.xlsx --date <YYYY-MM-DD> --role client_owner
   ```

   Where the team corrected one of these notes, the `team_correction` column shows it, and `accept_correction` keeps it. The client's decision wins over the team's.
3. The client approves the category list:

   ```bash
   itemizer gt approval-doc
   itemizer gt record-approval --date <YYYY-MM-DD> --evidence <saved email>
   ```

4. TEST is sealed and scored:

   ```bash
   itemizer gt seal
   itemizer evaluate
   itemizer acceptance record-review --date <YYYY-MM-DD> --evidence <saved email>
   itemizer acceptance d3
   ```

After `gt seal`, labels can no longer change.

## Where things are

| What | Where |
|---|---|
| Who changed which note, and when | `data/bootstrap/labels/test_label_review_log.jsonl` |
| The frozen labels | `data/bootstrap/test_provisional.json`, then `test_sealed.json` |
| Every evaluation and refusal | `data/kpi/test_budget.jsonl` |
