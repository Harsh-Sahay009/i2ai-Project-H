"""Offline shipment-level review export; never allocates expenses to invoices.

Saved model predictions remain immutable. Human decisions are an optional,
explicit row-scoped overlay. Output is candidate extraction, not payment approval.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
import csv
from decimal import Decimal
import json
from pathlib import Path
import re

import openpyxl

from itemizer.bootstrap.data import fingerprint, sha256_file

_BALANCE_AMOUNT = re.compile(
    r"\b(?:balance\s+due(?:\s+is)?|still\s+owe|outstanding\s+balance|short[ -]?paid)"
    r"\s*[:=-]?\s*\$?\s*(\d[\d, ]*(?:\.\d{1,2})?)", re.IGNORECASE)


def build_review(rows: list[dict], predictions: dict, overlay: dict | None = None) -> dict:
    overlay = overlay or {}
    if len({r["row_id"] for r in rows}) != len(rows):
        raise ValueError("source row IDs must be unique")
    unknown = set(overlay) - {r["row_id"] for r in rows}
    if unknown:
        raise ValueError(f"overlay references unknown rows: {sorted(unknown)}")
    grouped = defaultdict(list)
    for row in rows:
        bol = row["sap_bol"]
        if bol is not None and not isinstance(bol, str):
            raise ValueError("SAP BOL must be text; numeric identifiers can lose leading zeros")
        bol = bol.strip() if bol else None
        key = ("present", bol, fingerprint(row["note"])) if bol else (
            "missing", row["row_id"], fingerprint(row["note"]))
        grouped[key].append(row)
    groups, charges, context = [], [], []
    for (_, _, fp), members in grouped.items():
        bol = members[0]["sap_bol"]
        bol = bol.strip() if bol else None
        result = predictions.get(fp)
        flags = [] if bol else ["missing_sap_bol"]
        if result is None:
            flags.append("missing_prediction")
            result = dict(status="review", items=[], no_charge_stated=False)
        decisions = [overlay.get(r["row_id"]) for r in members]
        decision = decisions[0]
        if any(d != decision for d in decisions):
            raise ValueError("conflicting or partially scoped overlay on a joined shipment group")
        if decision:
            if not decision.get("decision_file"):
                raise ValueError("overlay requires decision_file provenance")
            if (decision.get("expected_fingerprint") != fp
                    or "expected_sap_bol" not in decision
                    or decision["expected_sap_bol"] != bol):
                raise ValueError("overlay source identity does not match this BOL/description")
            flags.extend(decision.get("flags", []))
        effective = decision if decision is not None and "items" in decision else result
        if result.get("status") != "ok" and not (decision and "items" in decision):
            flags.append(result.get("review_reason") or "model_review")
        gid = f"g_{members[0]['row_id']}_{fp[:8]}"
        group = dict(group_id=gid, sap_bol=bol, fingerprint=fp,
                     note_id=result.get("note_id"), description=members[0]["note"],
                     source_row_ids=[r["row_id"] for r in members],
                     invoice_bill_ids=sorted({r["invoice_bill_id"] for r in members}),
                     carrier_invoices=sorted({r["carrier_invoice"] for r in members}),
                     shipment_ids=sorted({r["shipment"] for r in members}),
                     source_disputed_amounts=sorted({r["disputed"] for r in members}),
                     repeated_join_rows=len(members)-1, flags=flags,
                     decision_file=decision.get("decision_file") if decision else None,
                     decision_status=decision.get("decision_status") if decision else None,
                     no_charge_stated=effective.get("no_charge_stated", False))
        for ordinal, item in enumerate(effective.get("items", []), 1):
            output = deepcopy(item)
            output.update(group_id=gid, sap_bol=bol, item=ordinal,
                          provenance="human_overlay" if effective is decision else "saved_model",
                          decision_file=group["decision_file"])
            # Evidence may quote only the amount. Compare explicitly named
            # balance amounts in the description, without swallowing a different
            # unmapped fee merely because a balance also occurs in that note.
            generic_balance = item["category"] == "other_unmapped" and any(
                Decimal(match.replace(",", "").replace(" ", "")) == Decimal(str(item["amount"]))
                for match in _BALANCE_AMOUNT.findall(group["description"])
            ) if item.get("amount") is not None else False
            if generic_balance:
                flags.append("unmapped_balance_context")
            destination = context if (item["category"] == "short_paid"
                or item["line_type"] == "already_paid" or generic_balance) else charges
            destination.append(output)
        groups.append(group)
    # Distinct descriptions can be revisions of a charge; retain candidates and
    # flag category overlaps rather than inventing a shipment financial total.
    by_category = defaultdict(set)
    for item in charges:
        if item["sap_bol"]:
            by_category[(item["sap_bol"], item["category"])].add(item["group_id"])
    overlaps = set().union(*(ids for ids in by_category.values() if len(ids) > 1))
    for group in groups:
        if group["group_id"] in overlaps:
            group["flags"].append("possible_overlapping_descriptions")
        group["flags"] = sorted(set(group["flags"]))
        group["status"] = "review" if group["flags"] else "candidate"
    return dict(schema_version=1, payment_approval=False, invoice_allocation=False,
                groups=groups, charges=charges, balance_context=context,
                source_rows=deepcopy(rows), summary=dict(
                    source_rows=len(rows), shipment_description_groups=len(groups),
                    repeated_join_rows=len(rows)-len(groups),
                    missing_bol_rows=sum(not r["sap_bol"] or not r["sap_bol"].strip() for r in rows),
                    expense_candidate_items=len(charges), balance_context_items=len(context),
                    groups_requiring_review=sum(g["status"] == "review" for g in groups)))


def load_source(path: Path) -> list[dict]:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = next(s for s in workbook.worksheets if s.title != "Sheet1")
        iterator = sheet.iter_rows(values_only=True)
        headers = list(next(iterator))
        names = dict(sap_bol="SAP BOL", invoice_bill_id="Invoice/Bill ID",
                     carrier_invoice="Carrier Invoice", shipment="SHIPMENT_GID",
                     note="Descritipion", disputed="Delta")
        positions = {k: headers.index(v) for k, v in names.items()}
        rows = []
        for number, cells in enumerate(iterator, 2):
            if all(c is None for c in cells):
                continue
            row = {k: cells[index] for k, index in positions.items()}
            if row["sap_bol"] is not None and not isinstance(row["sap_bol"], str):
                raise ValueError(f"SAP BOL in row {number} must be stored as text")
            row.update(row_id=f"R{number:04d}")
            for key in ("invoice_bill_id", "carrier_invoice", "shipment", "note"):
                row[key] = "" if row[key] is None else str(row[key])
            row["disputed"] = str(row["disputed"])
            rows.append(row)
        return rows
    finally:
        workbook.close()


def write_review(output: Path, report: dict) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "shipment_review.json").write_text(json.dumps(report, indent=2) + "\n")
    for name in ("groups", "charges", "balance_context", "source_rows"):
        records = report[name]
        fields = list(dict.fromkeys(key for record in records for key in record))
        with (output / f"{name}.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for record in records:
                writer.writerow({key: json.dumps(value) if isinstance(value, (list, dict)) else value
                                 for key, value in record.items()})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--overlay", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    overlay = None
    if args.overlay:
        envelope = json.loads(args.overlay.read_text())
        if envelope.get("dataset_sha256") != sha256_file(args.source):
            raise ValueError("overlay source workbook hash does not match")
        overlay = envelope["rows"]
    report = build_review(load_source(args.source), json.loads(args.predictions.read_text()), overlay)
    report["input_sha256"] = {"source": sha256_file(args.source),
                              "predictions": sha256_file(args.predictions)}
    if args.overlay:
        report["input_sha256"]["overlay"] = sha256_file(args.overlay)
    write_review(args.output, report)
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
