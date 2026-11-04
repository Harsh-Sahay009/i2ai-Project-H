"""The `itemizer` command: `gt` creates D1 and D2, and `run`, `evaluate` and `acceptance` carry D3."""
from __future__ import annotations

import json
import os
from pathlib import Path

import typer

from .bootstrap import labels as lb
from .bootstrap import split as sp
from .bootstrap import taxonomy as tx
from .bootstrap.data import Config, ContractError, Workspace, group_notes, load_config, load_export, sha256_file

# Locals are never shown on a crash: they can hold the API key or a note.
app = typer.Typer(no_args_is_help=True, help="Freight Invoice Itemizer.", pretty_exceptions_show_locals=False)
gt = typer.Typer(no_args_is_help=True, help="Create D1 (charge category list) and D2 (locked test set).")
app.add_typer(gt, name="gt")
acceptance_app = typer.Typer(no_args_is_help=True, help="Check a deliverable against its done-when conditions.")
app.add_typer(acceptance_app, name="acceptance")

CATEGORIES = Path("taxonomy/categories.yaml")
WORKED_EXAMPLES = Path("prompts/fewshot_v1.yaml")
APPROVAL = Path("taxonomy/approval.yaml")


class Context:
    """Loads settings and the dataset for one command. Commands print counts only, never note text."""

    def __init__(self, config: Path):
        self.root = Path.cwd()
        self.cfg: Config = load_config(self.root / config)
        self.ws = Workspace(self.cfg, self.root)
        self.export = self.root / self.cfg.source_file
        if not self.export.exists():
            raise ContractError(f"dataset file not found: {self.cfg.source_file}")
        self.rows, self.examples = load_export(self.export, self.cfg.examples_sheet)
        self.notes = group_notes(self.rows, self.cfg.large_dispute_usd)

    def manifest(self) -> dict:
        manifest = self.ws.read_json("split_manifest.json")
        if manifest["dataset_sha256"] != sha256_file(self.export):
            raise ContractError("the dataset file changed after the split was made")
        return manifest

    def categories(self) -> list[dict]:
        taxonomy = tx.load_taxonomy(self.root / CATEGORIES)
        problems = tx.validate_taxonomy(taxonomy, self.notes)
        if problems:
            raise ContractError("the taxonomy has problems: " + "; ".join(problems))
        return taxonomy["categories"]

    def codes(self) -> set[str]:
        return {c["code"] for c in self.categories()}


Config_ = typer.Option(Path("config/bootstrap.yaml"), "--config", help="Settings file.")


def _show(payload: object) -> None:
    typer.echo(json.dumps(payload, indent=2, sort_keys=True, default=str))


def _guard(function):
    """Show broken rules as plain messages rather than tracebacks."""
    import functools

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except ContractError as exc:
            typer.secho(f"Stopped: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2) from exc
        except (typer.Exit, typer.Abort):
            raise
        except Exception as exc:
            if os.environ.get("ITEMIZER_DEBUG"):
                raise
            typer.secho(f"Stopped: an unexpected {type(exc).__name__}. Its message is hidden because it can quote a note. "
                        "Set ITEMIZER_DEBUG=1 to see it.", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=3) from None

    return wrapper


@gt.command("profile")
@_guard
def profile_command(config: Path = Config_) -> None:
    """Count rows, notes, carriers and dollars, next to the scope's figures."""
    ctx = Context(config)
    report = sp.profile(ctx.rows, ctx.notes)
    path = ctx.ws.write_json("profile.json", report)
    ctx.ws.log("profile", [ctx.export], [path])
    _show(report)


@gt.command("scan")
@_guard
def scan_command(config: Path = Config_) -> None:
    """Scan notes for emails, phone numbers and possible names. Details stay in the local report."""
    ctx = Context(config)
    report = sp.scan(ctx.notes)
    path = ctx.ws.write_json("scan_report.json", report)
    ctx.ws.log("scan", [ctx.export], [path])
    _show({"counts": report["counts"], "notes_flagged": report["notes_flagged"], "details_in": str(path.relative_to(ctx.root))})


@gt.command("scan-decision")
@_guard
def scan_decision_command(
    decision: str = typer.Argument(..., help="exclude_flagged leaves flagged notes out of any send; accept sends them."),
    by: str = typer.Option(..., help="Who decided."),
    reason: str = typer.Option(..., help="Why."),
    config: Path = Config_,
) -> None:
    """Record what to do about notes the scan flagged. External sends stay blocked until this exists."""
    if decision not in ("exclude_flagged", "accept"):
        raise ContractError("decision must be exclude_flagged or accept")
    ctx = Context(config)
    path = ctx.ws.write_json("scan_decision.json", {"decision": decision, "by": by, "reason": reason})
    ctx.ws.log("scan-decision", [], [path], decision=decision)
    typer.echo(f"Recorded: {decision}")


@gt.command("split")
@_guard
def split_command(force: bool = typer.Option(False, help="Replace an existing split, only before packs exist."), config: Path = Config_) -> None:
    """Assign every distinct note to TEST, RESERVE, TRAIN or VALIDATION."""
    ctx = Context(config)
    blank = sum("empty_note" in r.flags for r in ctx.rows)
    seen = set(ctx.ws.read_json("seen_in_draft.json")) if ctx.ws.exists("seen_in_draft.json") else set()
    locked = ctx.ws.exists("packs.json") or ctx.ws.exists("seal_record.json")
    if not locked:  # a note with tool output is no longer blind, so a new split must not put it in TEST or RESERVE
        for results in (ctx.root / ctx.cfg.data_root / "runs").glob("run_*/note_results.json"):
            seen |= set(json.loads(results.read_text(encoding="utf-8")))
    pinned = set(ctx.examples)
    if (ctx.root / CATEGORIES).exists():  # notes quoted as D1 examples stay in TRAIN
        pinned |= {e["fingerprint"] for c in tx.load_taxonomy(ctx.root / CATEGORIES)["categories"] for e in c["examples"]}
    manifest = sp.build_split(ctx.notes, ctx.cfg, pinned, sha256_file(ctx.export), blank, never_test=seen)
    if ctx.ws.exists("split_manifest.json"):
        same = ctx.ws.read_json("split_manifest.json")["notes"] == json.loads(json.dumps(manifest["notes"], default=str))
        if not same:
            if locked:
                raise ContractError("labelling has started, so the split is locked")
            if not force:
                raise ContractError("a different split already exists; pass --force to replace it")
    path = ctx.ws.write_json("split_manifest.json", manifest)
    summary = sp.summarize(manifest)
    ctx.ws.log("split", [ctx.export], [path], seed=ctx.cfg.seed)
    _show({"seed": ctx.cfg.seed, "blank_note_rows": blank, "pinned_to_train": len(manifest["pinned_to_train"]), **summary})
    if summary["VALIDATION"]["notes"] < ctx.cfg.min_validation_notes:
        typer.secho(f"Warning: VALIDATION has fewer than {ctx.cfg.min_validation_notes} notes.", fg=typer.colors.YELLOW, err=True)


@gt.command("draft-taxonomy")
@_guard
def draft_command(
    send: bool = typer.Option(False, "--send", help="Actually send notes to the model. Without this, only show what would go."),
    sample: int = typer.Option(300, help="How many TRAIN notes to send."),
    model: str = typer.Option(tx.DEFAULT_MODEL, help="Model id."),
    proposal_file: Path = typer.Option(None, help="JSON proposal written outside this command, checked the same way as a model's."),
    config: Path = Config_,
) -> None:
    """Draft the D1 category list from TRAIN notes, and write it for the team to edit."""
    ctx = Context(config)
    manifest = ctx.manifest()
    excluded = sp.check_external_send(ctx.ws)
    chosen = tx.sample_train_notes(manifest, ctx.notes, excluded, sample, ctx.cfg.seed)
    tx.assert_train_only(chosen, manifest)
    system, user = tx.build_prompt(chosen, ctx.notes)
    digest = tx.prompt_hash(system, user)
    # Anyone reading the prompt has read these notes, so they can never move to TEST or VALIDATION.
    ctx.ws.write_json("seen_in_draft.json", sorted(set(chosen) | set(
        ctx.ws.read_json("seen_in_draft.json") if ctx.ws.exists("seen_in_draft.json") else [])))
    if proposal_file is not None:
        proposal = tx.TaxonomyProposal.model_validate_json(proposal_file.read_text(encoding="utf-8"))
    elif send:
        proposal = tx.AnthropicDrafter(model).propose(system, user)
    else:
        prompt_path = ctx.ws.path("draft_prompt.txt")
        prompt_path.write_text(system + "\n\n" + user + "\n", encoding="utf-8")
        _show({"dry_run": True, "notes_to_send": len(chosen), "left_out_after_scan": len(excluded),
               "characters": len(system) + len(user), "model": model, "prompt_sha256": digest,
               "prompt_in": str(prompt_path.relative_to(ctx.root))})
        typer.echo("Nothing was sent. Add --send to send these notes to the model.")
        return
    taxonomy, report = tx.draft_taxonomy(proposal, chosen, ctx.notes, model, digest)
    path = ctx.root / CATEGORIES
    tx.write_taxonomy(path, taxonomy)
    report["problems"] = tx.validate_taxonomy(taxonomy, ctx.notes)
    report_path = ctx.ws.write_json("taxonomy_draft_report.json", report)
    ctx.ws.log("draft-taxonomy", [ctx.export], [path, report_path], model=model, prompt_sha256=digest)
    _show(report)


@gt.command("validate-taxonomy")
@_guard
def validate_command(config: Path = Config_) -> None:
    """Check the category list, including that no note text is in the Git-tracked file."""
    ctx = Context(config)
    problems = tx.validate_taxonomy(tx.load_taxonomy(ctx.root / CATEGORIES), ctx.notes)
    if problems:
        raise ContractError("; ".join(problems))
    typer.echo("The taxonomy passes.")


@gt.command("approval-doc")
@_guard
def approval_doc_command(config: Path = Config_) -> None:
    """Write the two-page document for the client owner. It holds real quotes, so it stays out of Git."""
    ctx = Context(config)
    path = ctx.ws.path("D1_category_list.html")
    path.write_text(tx.approval_document(tx.load_taxonomy(ctx.root / CATEGORIES), ctx.notes), encoding="utf-8")
    ctx.ws.log("approval-doc", [ctx.root / CATEGORIES], [path])
    typer.echo(f"Wrote {path.relative_to(ctx.root)}")


@gt.command("record-approval")
@_guard
def record_approval_command(
    role: str = typer.Option("client_owner", help="Approver's role."),
    date: str = typer.Option(..., help="Approval date, YYYY-MM-DD."),
    evidence: Path = typer.Option(..., help="File holding the written approval, such as a saved email."),
    config: Path = Config_,
) -> None:
    """Record the client's written approval of the category list."""
    ctx = Context(config)
    ctx.categories()
    record = tx.record_approval(ctx.root / CATEGORIES, ctx.root / APPROVAL, role, date, evidence)
    ctx.ws.log("record-approval", [ctx.root / CATEGORIES, evidence], [ctx.root / APPROVAL])
    _show(record)


@gt.command("label-packs")
@_guard
def label_packs_command(
    replacements: bool = typer.Option(False, help="Only write the pack for notes added by `gt final-strata --apply`."),
    train_suggestions: Path = typer.Option(None, help="JSON of model suggestions, allowed for the TRAIN pack only."),
    config: Path = Config_,
) -> None:
    """Write the labelling workbooks. TEST and VALIDATION packs contain no tool output."""
    ctx = Context(config)
    manifest, categories = ctx.manifest(), ctx.categories()
    if replacements:
        members = ctx.ws.read_json("packs.json").get("label_replacements")
        if not members:
            raise ContractError("there are no replacement notes")
        lb.write_pack(ctx.ws.path("packs/label_replacements.xlsx"), "TEST", members, ctx.notes, categories)
        typer.echo(f"Wrote the replacement pack with {len(members)} notes.")
        return
    suggestions = json.loads(train_suggestions.read_text(encoding="utf-8")) if train_suggestions else None
    packs = lb.build_packs(ctx.ws, manifest, ctx.notes, categories, suggestions)
    ctx.ws.log("label-packs", [ctx.root / CATEGORIES], [ctx.ws.path(f"packs/{name}.xlsx") for name in packs])
    _show({name: len(members) for name, members in packs.items()})


@gt.command("import-labels")
@_guard
def import_labels_command(
    pack: str = typer.Argument(..., help="label_A, label_B, label_single, spot_check, label_replacements, validation or train."),
    path: Path = typer.Argument(..., help="The filled workbook."),
    labeller: str = typer.Option(..., help="Who labelled it."),
    config: Path = Config_,
) -> None:
    """Check a returned workbook and report every failure per row."""
    ctx = Context(config)
    ctx.manifest()
    result = lb.import_labels(ctx.ws, pack, path, labeller, ctx.notes, ctx.codes())
    ctx.ws.log("import-labels", [path], [ctx.ws.path(f"labels/{pack}.json")], pack=pack, errors=result["errors"])
    _show(result)
    if result["errors"]:
        typer.secho(f"Fix the rows in {ctx.ws.path(f'labels/{pack}.errors.csv').relative_to(ctx.root)} and import again.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)


@gt.command("client-pack")
@_guard
def client_pack_command(config: Path = Config_) -> None:
    """Compute agreement, and write the review workbook with all 50 double-labelled notes."""
    ctx = Context(config)
    report = lb.write_client_pack(ctx.ws, ctx.notes, ctx.categories())
    ctx.ws.log("client-pack", [], [ctx.ws.path("agreement.json"), ctx.ws.path("packs/client_review.xlsx")])
    _show({k: (len(v) if k == "disagreements" else v) for k, v in report.items()})


@gt.command("import-client")
@_guard
def import_client_command(
    path: Path = typer.Argument(..., help="The returned review workbook."),
    date: str = typer.Option(..., help="Review date, YYYY-MM-DD."),
    role: str = typer.Option(..., help="Reviewer's role: client_owner, or team_provisional for a team member. Required, because it decides whether TEST can be sealed."),
    config: Path = Config_,
) -> None:
    """Read the client's review. Their decision becomes the gold label."""
    ctx = Context(config)
    result = lb.import_client_review(ctx.ws, path, role, date, ctx.notes, ctx.codes())
    ctx.ws.log("import-client", [path], [ctx.ws.path("client_review.json")], errors=result["errors"])
    _show(result)
    if result["errors"]:
        raise typer.Exit(code=1)


@gt.command("final-strata")
@_guard
def final_strata_command(apply: bool = typer.Option(False, help="Move the notes listed."), config: Path = Config_) -> None:
    """Compare the labelled mix with 100/100, and list replacements from the reserve if it is off."""
    ctx = Context(config)
    manifest = ctx.manifest()
    result = lb.final_strata(ctx.ws, manifest, ctx.notes, apply)
    if apply and result["replace"]:
        path = ctx.ws.write_json("split_manifest.json", manifest)
        ctx.ws.log("final-strata", [], [path], moved=len(result.get("add_note_ids", [])))
    _show(result)


@gt.command("draft-test-labels")
@_guard
def draft_test_labels_command(
    send: bool = typer.Option(False, "--send", help="Actually send TEST notes to the model. Without this, only show what would go."),
    first_model: str = typer.Option(None, help="The model for labeller A and the single-labelled notes."),
    second_model: str = typer.Option(None, help="The model for labeller B."),
) -> None:
    """Have a model draft the TEST labels (ADR 0015). Each is marked as a draft until a person has checked it."""
    import datetime as dt

    from .model_labels import FIRST_LABELLER, SECOND_LABELLER, draft_test_labels, plan_test_labels

    first, second = first_model or FIRST_LABELLER, second_model or SECOND_LABELLER
    if not send:
        _show(plan_test_labels(Path.cwd(), first, second))
        typer.echo("Nothing was sent. Add --send to send these notes to the model.")
        return
    report = draft_test_labels(Path.cwd(), dt.date.today().isoformat(), first, second)
    _show(report)
    if not report["complete"]:
        typer.secho("Some notes have no label. Run this again to continue, or see the errors file for each pack.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)


@gt.command("rename-category")
@_guard
def rename_category_command(
    old: str = typer.Argument(..., help="The code to change."),
    new: str = typer.Argument(..., help="The new code."),
    merge: bool = typer.Option(False, "--merge", help="Move the category into one that already exists."),
    config: Path = Config_,
) -> None:
    """Change a category's code in the list, the worked examples and every label, keeping who wrote each label."""
    ctx = Context(config)
    lb.check_not_sealed(ctx.ws)
    tx.rename_in_taxonomy(ctx.root / CATEGORIES, old, new, merge, ctx.notes)
    examples = tx.rename_in_worked_examples(ctx.root / WORKED_EXAMPLES, old, new)
    changed = lb.rename_category(ctx.ws, old, new)
    ctx.ws.log("rename-category", [], [ctx.root / CATEGORIES], old=old, new=new, merge=merge)
    _show({"old": old, "new": new, "items_changed": changed, "worked_examples_changed": examples})
    typer.echo("The prompt changed, so the next step is `itemizer run`, then `itemizer evaluate --extra-peek \"<reason>\"`. "
               "Any earlier approval of the list no longer applies. If the client's workbook was written, run `itemizer gt client-pack` again.")


@gt.command("label-review-pack")
@_guard
def label_review_pack_command(config: Path = Config_) -> None:
    """Write every TEST label to a workbook for people to check, with no tool output."""
    ctx = Context(config)
    result = lb.write_label_review(ctx.ws, ctx.manifest(), ctx.notes, ctx.categories())
    ctx.ws.log("label-review-pack", [], [ctx.ws.path("packs/test_label_review.xlsx")], notes=result["notes"])
    _show(result)


@gt.command("import-label-review")
@_guard
def import_label_review_command(
    path: Path = typer.Argument(..., help="The reviewed workbook."),
    reviewer: str = typer.Option(..., help="Who reviewed it."),
    date: str = typer.Option(..., help="Review date, YYYY-MM-DD."),
    config: Path = Config_,
) -> None:
    """Take back what people checked or corrected. deliverables/reviewing_test_labels.md explains the steps."""
    ctx = Context(config)
    result = lb.import_label_review(ctx.ws, path, reviewer, date, ctx.manifest(), ctx.notes, ctx.codes())
    ctx.ws.log("import-label-review", [path], [], reviewed=result["reviewed"], corrected=result["corrected"], errors=result["errors"])
    _show(result)
    if result["errors"]:
        typer.secho(f"Nothing changed. Fix the rows in {ctx.ws.path('labels/test_label_review.errors.csv').relative_to(ctx.root)} and import again.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)


@gt.command("seal")
@_guard
def seal_command(
    mapping: Path = typer.Option(None, help="YAML mapping from draft codes to approved codes."),
    provisional: bool = typer.Option(False, "--provisional", help="Freeze TEST on team-resolved labels, before the client's review."),
    config: Path = Config_,
) -> None:
    """Seal TEST when every condition holds, then release unused reserve notes."""
    import yaml

    ctx = Context(config)
    manifest = ctx.manifest()
    if provisional:
        record = lb.seal_provisional(ctx.ws, manifest, ctx.notes, ctx.codes())
        ctx.ws.log("seal-provisional", [], [ctx.ws.path("test_provisional.json")], sha256=record["sha256"])
        _show(record)
        return
    approved = tx.approved_codes(ctx.root / CATEGORIES, ctx.root / APPROVAL)
    code_map = yaml.safe_load(mapping.read_text(encoding="utf-8")) if mapping else None
    record = lb.seal(ctx.ws, manifest, ctx.notes, approved, code_map)
    ctx.ws.log("seal", [], [ctx.ws.path("test_sealed.json"), ctx.ws.path("split_manifest.json")], sha256=record["sha256"])
    _show(record)


def _show_outcome(outcome) -> None:
    root = Path.cwd()
    coverage = outcome.coverage
    _show({
        "run_id": outcome.run_id, "rows": outcome.rows, "notes": outcome.notes, "outcomes": outcome.outcomes,
        "reasons": outcome.reasons, "minutes": round(outcome.minutes, 2), "cost_this_run_usd": str(outcome.new_calls_usd),
        "cost_when_first_answered_usd": str(outcome.measured_usd), "notes_from_cache": outcome.cached_notes,
        "coverage_rows_on_these_rows": coverage["rows"]["share"], "coverage_usd_on_these_rows": coverage["usd"]["share"],
        "workbook": str(outcome.workbook.relative_to(root)) if outcome.workbook.is_relative_to(root) else str(outcome.workbook),
    })


@app.command("run")
@_guard
def run_command(
    model: str = typer.Option(None, help="A name from config/models.yaml. Without this, the default model."),
    set_name: str = typer.Option(None, "--set", help="train or validation, for development. Without this, all rows."),
    limit: int = typer.Option(None, help="Only this many notes of the set."),
    export: Path = typer.Option(None, help="Another export file. Without this, the dataset file."),
) -> None:
    """Itemize an export and write the workbook. A run on all rows of the dataset waits until TEST is frozen."""
    from .pipeline import run

    _show_outcome(run(Path.cwd(), model_name=model, set_name=set_name, limit=limit, export=export))


@app.command("evaluate")
@_guard
def evaluate_command(
    run_id: str = typer.Option(None, "--run", help="The run to score. Without this, the newest run on all rows."),
    milestone: str = typer.Option("d3", help="The milestone this evaluation belongs to, from kpi.milestones."),
    extra_peek: str = typer.Option(None, "--extra-peek", help="Spend past the TEST budget on purpose, for this reason. It is logged and shown beside the result."),
) -> None:
    """Score a run on TEST and report the Level gates. Aggregates only."""
    from .pipeline import evaluate_run

    snapshot = evaluate_run(Path.cwd(), run_id, milestone, extra_peek)
    _show({key: snapshot[key] for key in ("run_id", "milestone", "labels_status", "accuracy_scope", "levels", "coverage", "accuracy", "invariants", "test_budget")})


@app.command("models")
@_guard
def models_command() -> None:
    """List the models you can use. To add one on a known API, add an entry to config/models.yaml."""
    from .providers import load_models, load_secret

    specs, default = load_models(Path.cwd() / "config/models.yaml")
    lines = []
    for name, spec in sorted(specs.items()):
        key = "not needed"
        if spec.api_key_env:
            try:
                load_secret(spec.api_key_env, Path.cwd())
                key = f"{spec.api_key_env} is set"
            except ContractError:
                key = f"{spec.api_key_env} is not set"
        lines.append({"name": name, "default": name == default, "provider": spec.provider, "model": spec.model, "effort": spec.effort,
                      "key": key, "usd_per_mtok_in_out": [str(spec.input_usd_per_mtok), str(spec.output_usd_per_mtok)]})
    _show(lines)


@app.command("compare-models")
@_guard
def compare_command(
    models: str = typer.Option(..., help="Comma-separated names from config/models.yaml. The first is the reference."),
    set_name: str = typer.Option("train", "--set", help="train or validation. TEST never chooses between candidates."),
    limit: int = typer.Option(None, help="Only this many notes."),
) -> None:
    """Run several models on the same notes and compare them on the same measures."""
    from .compare import compare_models, format_table

    report = compare_models(Path.cwd(), [name.strip() for name in models.split(",") if name.strip()], set_name, limit)
    typer.echo(format_table(report))
    typer.echo(f"Report: {report['report_path'].relative_to(Path.cwd())}")


@acceptance_app.command("d3")
@_guard
def acceptance_d3_command(run_id: str = typer.Option(None, "--run", help="The run to report. Without this, the newest on all rows.")) -> None:
    """Write the one-page status for D1, D2 and D3."""
    from .acceptance import d3_check

    summary = d3_check(Path.cwd(), run_id)
    d3 = summary["d3"]
    _show({"d1": summary["d1"], "d2": summary["d2"], "d3": {key: d3.get(key) for key in ("status", "reason", "run_id", "labels_status", "client_review")},
           "level1": d3.get("level1"), "page": str(summary["page"].relative_to(Path.cwd()))})


@acceptance_app.command("record-review")
@_guard
def acceptance_review_command(
    date: str = typer.Option(..., help="Review date, YYYY-MM-DD."),
    evidence: Path = typer.Option(..., help="A file showing the client has seen the prototype, such as a saved email."),
    run_id: str = typer.Option(None, "--run", help="The run they saw. Without this, the newest on all rows."),
) -> None:
    """Record that the client has seen the prototype."""
    from .acceptance import record_review

    _show(record_review(Path.cwd(), date, evidence, run_id))


if __name__ == "__main__":
    app()
