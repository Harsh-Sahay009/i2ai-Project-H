"""The `itemizer` command. For now it holds `gt`, which creates D1 and D2."""
from __future__ import annotations

import json
from pathlib import Path

import typer

from .bootstrap import split as sp
from .bootstrap.data import Config, ContractError, Workspace, group_notes, load_config, load_export, sha256_file

app = typer.Typer(no_args_is_help=True, help="Freight Invoice Itemizer.")
gt = typer.Typer(no_args_is_help=True, help="Create D1 (charge category list) and D2 (locked test set).")
app.add_typer(gt, name="gt")

CATEGORIES = Path("taxonomy/categories.yaml")
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
    pinned = set(ctx.examples)
    if (ctx.root / CATEGORIES).exists():  # notes quoted as D1 examples stay in TRAIN
        pinned |= {e["fingerprint"] for c in tx.load_taxonomy(ctx.root / CATEGORIES)["categories"] for e in c["examples"]}
    manifest = sp.build_split(ctx.notes, ctx.cfg, pinned, sha256_file(ctx.export), blank, never_test=seen)
    if ctx.ws.exists("split_manifest.json"):
        same = ctx.ws.read_json("split_manifest.json")["notes"] == json.loads(json.dumps(manifest["notes"], default=str))
        if not same:
            if ctx.ws.exists("packs.json") or ctx.ws.exists("seal_record.json"):
                raise ContractError("labelling has started, so the split is locked")
            if not force:
                raise ContractError("a different split already exists; pass --force to replace it")
    path = ctx.ws.write_json("split_manifest.json", manifest)
    summary = sp.summarize(manifest)
    ctx.ws.log("split", [ctx.export], [path], seed=ctx.cfg.seed)
    _show({"seed": ctx.cfg.seed, "blank_note_rows": blank, "pinned_to_train": len(manifest["pinned_to_train"]), **summary})
    if summary["VALIDATION"]["notes"] < ctx.cfg.min_validation_notes:
        typer.secho(f"Warning: VALIDATION has fewer than {ctx.cfg.min_validation_notes} notes.", fg=typer.colors.YELLOW, err=True)


if __name__ == "__main__":
    app()
