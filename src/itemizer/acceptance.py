"""One page showing where D1, D2 and D3 stand, for presenting them together. It holds no note text."""
from __future__ import annotations

import datetime as dt
import html
import json
from pathlib import Path

from . import kpi
from .bootstrap import split as sp
from .bootstrap import taxonomy as tx
from .bootstrap.data import ContractError, sha256_file
from .output import largest_shipments
from .pipeline import APPROVAL, CATEGORIES, Project, latest_full_run, load_project, load_run

REVIEW_RECORD = "reports/client_review_d3.json"
_CONDITION_NAMES = {"cov_usd": "Coverage of disputed dollars", "cov_rows": "Coverage of rows", "acc": "Accuracy on covered rows"}


def record_review(root: Path, date: str, evidence: Path) -> dict:
    """Record that the client has seen the prototype. D3 stays open until this exists."""
    project = load_project(root)
    if not evidence.exists():
        raise ContractError(f"evidence file not found: {evidence}")
    try:
        dt.date.fromisoformat(date)
    except ValueError:
        raise ContractError("the date must look like YYYY-MM-DD") from None
    record = {"date": date, "evidence_sha256": sha256_file(evidence)}
    target = project.data_root / REVIEW_RECORD
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    project.ws.log("acceptance-record-review", [evidence], [target])
    return record


def _d1(project: Project) -> dict:
    path = project.root / CATEGORIES
    if not path.exists():
        return {"status": "not_drafted", "categories": 0}
    taxonomy = tx.load_taxonomy(path)
    regular = [c for c in taxonomy["categories"] if c["code"] != "other_unmapped"]
    approved = tx.approved_codes(path, project.root / APPROVAL) is not None
    return {"status": "approved" if approved else "draft", "categories": len(regular), "version": taxonomy.get("version")}


def _d2(project: Project) -> dict:
    ws = project.ws
    sealed, provisional = ws.exists("seal_record.json"), ws.exists("provisional_record.json")
    status = "sealed" if sealed else ("provisional" if provisional else "not_frozen")
    labelled = 0
    if ws.exists("labels/label_single.json"):
        labelled += len(ws.read_json("labels/label_single.json")["labels"])
    if ws.exists("labels/label_A.json"):
        labelled += len(ws.read_json("labels/label_A.json")["labels"])
    result = {"status": status, "labelled_notes": labelled, "target_notes": len(sp.notes_in_set(project.split, "TEST"))}
    if ws.exists("agreement.json"):
        agreement = ws.read_json("agreement.json")
        result["agreement"] = {"notes_compared": agreement["notes_compared"], "cohens_kappa_category": agreement["cohens_kappa_category"],
                               "amount_exact_match": agreement["amount_exact_match"], "disagreements": len(agreement["disagreements"])}
    return result


def _d3(project: Project, run_id: str | None) -> tuple[dict, list[dict]]:
    run_id = run_id or latest_full_run(project)
    result: dict = {"run_id": run_id, "client_review": None}
    review = project.data_root / REVIEW_RECORD
    if review.exists():
        result["client_review"] = json.loads(review.read_text(encoding="utf-8"))
    if run_id is None:
        return {**result, "status": "open", "reason": "no_run_on_all_rows"}, []
    manifest, rows, notes = load_run(project, run_id)
    if manifest.set_name != "all":
        raise ContractError("the D3 check needs a run on all rows of the dataset file")
    categories = project.categories()
    shipments = largest_shipments(rows, notes, categories)[:10]
    result["model"] = manifest.model.get("name")
    snapshot_path = kpi.snapshot_path(project.data_root, run_id, "d3")
    if not snapshot_path.exists():
        return {**result, "status": "open", "reason": "not_evaluated"}, shipments
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    level = snapshot["levels"]["level1"]
    result.update(level1=level, labels_status=snapshot["labels_status"], accuracy_scope=snapshot["accuracy_scope"],
                  coverage=snapshot["coverage"], invariants=snapshot["invariants"], accuracy=snapshot["accuracy"])
    if level["status"] != "pass":
        return {**result, "status": "open", "reason": level.get("reason") or "level1_not_met"}, shipments
    if result["client_review"] is None:
        return {**result, "status": "open", "reason": "client_review_missing"}, shipments
    if snapshot["labels_status"] != "sealed":  # the result can still change when the client's labels are sealed
        return {**result, "status": "open", "reason": "labels_provisional"}, shipments
    return {**result, "status": "done", "reason": None}, shipments


def _percent(value: float | None) -> str:
    return "not measured" if value is None else f"{value * 100:.1f}%"


def _money(value: object) -> str:
    return f"${float(str(value)):,.2f}"


def _level_rows(level: dict) -> str:
    lines = []
    for key, condition in level["conditions"].items():
        interval = f"{_percent(condition.get('ci_low'))} to {_percent(condition.get('ci_high'))}"
        lines.append(f"<tr><td>{_CONDITION_NAMES.get(key, html.escape(key))}</td><td>{_percent(condition.get('value'))}</td>"
                     f"<td>{_percent(condition.get('target'))}</td><td>{'Yes' if condition.get('met') else 'No'}</td>"
                     f"<td>{interval}</td><td>{condition.get('n', 0)}</td></tr>")
    return "".join(lines)


def _page(summary: dict, shipments: list[dict]) -> str:
    d1, d2, d3 = summary["d1"], summary["d2"], summary["d3"]
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'><title>D1, D2 and D3 status</title><style>"
        "@page{margin:1.5cm}body{font:11pt/1.4 Arial,sans-serif;color:#222;max-width:60em;margin:1.5em auto;padding:0 1em}"
        "h1{font-size:17pt;margin:0 0 .2em}h2{font-size:13pt;margin:1.2em 0 .3em}"
        "table{border-collapse:collapse;width:100%}th,td{border:1px solid #bbb;padding:3pt 6pt;text-align:left;vertical-align:top}"
        "th{background:#eee}.flag{background:#fff2cc;padding:4pt 8pt;margin:.5em 0}</style></head><body>",
        "<h1>Freight Invoice Itemization: D1, D2 and D3 status</h1>",
        "<h2>D1: charge category list</h2>",
        f"<p>Status: <b>{html.escape(d1['status'])}</b>. {d1['categories']} categories, plus a catch-all.</p>",
        "<h2>D2: locked test set</h2>",
        f"<p>Status: <b>{html.escape(d2['status'])}</b>. {d2['labelled_notes']} of {d2['target_notes']} notes labelled.</p>",
    ]
    if "agreement" in d2:
        agreement = d2["agreement"]
        parts.append(f"<p>Two labellers compared on {agreement['notes_compared']} notes: category agreement (Cohen's kappa) "
                     f"{agreement['cohens_kappa_category']}, amounts matching on {agreement['amount_exact_match']} notes, "
                     f"{agreement['disagreements']} disagreements.</p>")
    parts.append("<h2>D3: prototype on all rows, Level 1</h2>")
    parts.append(f"<p>Status: <b>{html.escape(d3['status'])}</b>"
                 + (f" ({html.escape(str(d3['reason']))})" if d3.get("reason") else "") + ".</p>")
    if "level1" in d3:
        if d3["labels_status"] == "provisional":
            parts.append("<p class='flag'>These results are <b>provisional</b>. They use labels the team resolved, "
                         "until the client has reviewed the 50 double-labelled notes.</p>")
        parts.append(f"<p>Level 1 result: <b>{html.escape(d3['level1']['status'])}</b>. A level is met when the measured value "
                     "reaches the target, with its range shown beside it. Accuracy is in-sample, because all notes come from one file.</p>")
        parts.append("<table><tr><th>Condition</th><th>Measured</th><th>Target</th><th>Met</th><th>Range</th><th>n</th></tr>"
                     f"{_level_rows(d3['level1'])}</table>")
        coverage = d3["coverage"]
        parts.append(f"<p>Dollar coverage without repeated invoices: {_percent(coverage['without_repeats']['usd']['share'])}. "
                     f"Invariant violations: {d3['invariants']['violations']}.</p>")
    else:
        parts.append("<p>No accuracy is shown, because the test set has not been scored yet.</p>")
    review = d3.get("client_review")
    parts.append(f"<p>Client review: {html.escape(review['date']) if review else 'not recorded yet'}.</p>")
    if shipments:
        parts.append("<h2>Largest disputes, each shipment counted once</h2>"
                     "<table><tr><th>Rank</th><th>Shipment</th><th>Rows</th><th>Largest dispute</th><th>Total on rows</th>"
                     "<th>Repeated rows</th><th>Share</th><th>Outcome</th><th>Main category</th></tr>")
        for line in shipments:
            parts.append(f"<tr><td>{line['rank']}</td><td>{html.escape(str(line['shipment']))}</td><td>{line['rows']}</td>"
                         f"<td>{_money(line['largest_dispute'])}</td><td>{_money(line['total_on_rows'])}</td><td>{line['repeated_rows']}</td>"
                         f"<td>{_percent(line['share_of_total'])}</td><td>{html.escape(str(line['outcome']))}</td>"
                         f"<td>{html.escape(str(line['main_category'] or ''))}</td></tr>")
        parts.append("</table>")
    parts.append("</body></html>\n")
    return "".join(parts)


def d3_check(root: Path, run_id: str | None = None) -> dict:
    """Write the summary. It works in every state, and never shows an accuracy that was not measured."""
    project = load_project(root)
    d3, shipments = _d3(project, run_id)
    summary = {"d1": _d1(project), "d2": _d2(project), "d3": d3,
               "largest_disputes": [{**line, "largest_dispute": str(line["largest_dispute"]), "total_on_rows": str(line["total_on_rows"])}
                                    for line in shipments]}
    folder = project.data_root / "reports"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "d3_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (folder / "d3_summary.html").write_text(_page(summary, shipments), encoding="utf-8")
    project.ws.log("acceptance-d3", [], [folder / "d3_summary.html"], status=d3["status"])
    return {**summary, "page": folder / "d3_summary.html"}
