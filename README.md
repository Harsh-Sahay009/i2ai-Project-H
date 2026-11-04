# Freight Invoice Itemizer

PPG pays carriers against an estimated freight charge. When a carrier bills more, a clerk explains the difference in a free-text note, and accountants read each note by hand. This tool turns those notes into itemized charges, each with a category, an amount and the exact words it came from. A row that does not add up is flagged, and the tool never edits an amount to make it add up. It does not decide whether a charge should be paid.

**Status:** the D3 prototype runs on the sample export. The labels behind its accuracy figure were drafted by Claude Opus and have not yet been checked by people (ADR 0015), so that figure shows agreement with those drafts and not correctness. See `openspec/changes/add-d3-thin-path/live-check.md`.

## Install

You need Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra llm --extra ui --group dev
```

The dataset is not in this repo, because this repo is public. Put the export file in the project's root, as named in `config/bootstrap.yaml`. Put your API key in a file named `.env`, as `CLAUDE_API_KEY=<key>`. Git ignores both, along with everything under `data/`.

## Use it

```bash
itemizer ui
```

Open <http://127.0.0.1:8000> to upload an export, see what the run would cost, run it, download the output Excel and see the KPIs. It serves your machine only.

The same from a terminal:

```bash
itemizer run --export <file.xlsx>   # another export
itemizer run --set train            # the dataset's TRAIN notes, for development
itemizer run                        # all rows of the dataset, once TEST is frozen
itemizer evaluate                   # score a run on all rows against TEST
itemizer acceptance d3              # write the D1, D2 and D3 status page
```

To try another model, add one entry to `config/models.yaml`, and compare it with `itemizer compare-models`. `architecture/docs/11-data-contracts.md` explains how.

## Where things are

| Path | What it holds |
|---|---|
| `src/itemizer/` | The tool. `bootstrap/` creates D1 and D2, and `ui/` is the local page |
| `config/`, `prompts/`, `taxonomy/` | Settings, models, prompts and the category list, with no note text |
| `tests/` | Tests on invented notes, with no network: `uv run pytest` |
| `architecture/` | The C4 model, design docs and ADRs. Start at `architecture/README.md` |
| `openspec/changes/` | What each change requires, with its tasks |
| `deliverables/` | How to review the test labels, how to run the meeting, and requests to PPG |
