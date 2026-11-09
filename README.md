# Freight Invoice Itemizer

PPG pays carriers against an estimated freight charge. When a carrier bills more, a clerk explains the difference in a free-text note, and accountants read each note by hand. This tool turns those notes into itemized charges, each with a category, an amount and the exact words it came from. A row that does not add up is flagged, and the tool never edits an amount to make it add up. It does not decide whether a charge should be paid.

**Current-data closeout (November 9, 2026):** the prototype, separate OpenAI evaluation, shipment-level export and assisted review are complete for the supplied export. The 200-note benchmark has 95.94% answered-note agreement and 94.5% strict yield against the existing reference, not independently double-labeled accuracy on all data. Review exclusions and the outstanding human/client/new-export acceptance requirements are explicit. Start with the [final methodology report](deliverables/final_methodology_report.md) and [rerun guide](deliverables/final_rerun_guide.md). Historical prototype results remain in `openspec/changes/add-d3-thin-path/live-check.md`.

The eight-page [final report PDF](output/pdf/Freight_Analytics_Final_Report.pdf) contains aggregate results and limitations; confidential review workbooks and source data remain private.

## Install

You need Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra llm --extra ui --group dev
```

The dataset is not in this repo, because this repo is public. Put the export file in the project's root, as named in `config/bootstrap.yaml`. Put your API key in a file named `.env`, as `CLAUDE_API_KEY=<key>`. Git ignores both, along with everything under `data/`.

## Use it

```bash
uv run itemizer ui
```

Open <http://127.0.0.1:8899> to upload an export, see what the run would cost, run it, download the output Excel and see the KPIs. It serves your machine only.

The same from a terminal:

```bash
uv run itemizer run --export <file.xlsx>   # another export
uv run itemizer run --set train            # the dataset's TRAIN notes, for development
uv run itemizer run                        # all rows of the dataset, once TEST is frozen
uv run itemizer evaluate                   # score a run on all rows against TEST
uv run itemizer acceptance d3              # write the D1, D2 and D3 status page
```

To try another model, add one entry to `config/models.yaml`, and compare it with `itemizer compare-models`. `architecture/docs/11-data-contracts.md` explains how.

## Local readiness and restoring shared labels

The local `codex/integrate-latest` branch combines the current `main` implementation with the readiness fixes. `itemizer doctor` validates local setup without model calls or file changes; exit 0 is setup readiness, not D3 acceptance. New splits also pin every prompt example to TRAIN. Existing locked splits are not changed.

The current local checkout is `/Users/harshsahay/.codex/workspaces/i2ai-Project-H`, outside iCloud-managed Desktop storage. The prior Desktop copy is preserved; do not mix their generated experiment records.

The shared `test_provisional.json` contains model-drafted labels, not human-reviewed ground truth. Keep it separate from a newly reconstructed split: those experiments have different TEST membership. Restoring the original experiment also requires its split manifest, provisional record, labeling/agreement records, and run/KPI artifacts. Do not create approval or freeze records merely to make the application run.

The local `data/incoming/alejandro/` folder preserves the received file and any portable review materials. A portable review workbook can support reading and corrections now, but must not be imported into the reconstructed experiment. Preserve the original label file and import a reviewed workbook only against its matching original TEST set with the supported review command.

On macOS with Python 3.14, an editable package may fail to import if its `.pth` file carries the hidden filesystem flag. Check with `ls -lO .venv/lib/python*/site-packages/*itemizer*.pth`. A local nonhidden `.pth` containing the absolute project `src` path restores discovery; this is an environment repair, not a change to extraction behavior. Recheck `uv run python -c "import itemizer"` after installation.

## Where things are

| Path | What it holds |
|---|---|
| `src/itemizer/` | The tool. `bootstrap/` creates D1 and D2, and `ui/` is the local page |
| `config/`, `prompts/`, `taxonomy/` | Settings, models, prompts and the category list, with no note text |
| `tests/` | Tests on invented notes, with no network: `uv run pytest` |
| `architecture/` | The C4 model, design docs and ADRs. Start at `architecture/README.md` |
| `openspec/changes/` | What each change requires, with its tasks |
| `deliverables/` | How to review the test labels, how to run the meeting, and requests to PPG |
