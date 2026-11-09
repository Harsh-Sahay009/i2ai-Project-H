## 1. Plan

- [x] 1.1 Write this change and ADR 0017, and edit the workbook requirements in `add-d3-thin-path`'s `d3-output` spec

## 2. Code

- [x] 2.1 Read `SAP BOL` and `Invoice/Bill ID` when present, and carry `sap_bol`, `bill_id` and `billed` into row results
- [x] 2.2 Group rows into charge lines, with each line's outcome, rows and possible double counts
- [x] 2.3 Write `Items`, `Charge Summary` and `Largest` at the new grain, and record the grain in `Run Info`
- [x] 2.4 Show the new `Largest` columns on the status page
- [x] 2.5 Give a run written before this change a plain message in `evaluate`
- [x] 2.6 Regenerate the JSON Schemas, and update `architecture/docs/11-data-contracts.md`
- [x] 2.7 Tests per scenario in `sap-bol-output-grain`, on invented notes

## 3. Check

- [x] 3.1 Test the branch from a clean export of its commit
- [x] 3.2 Run all rows of the dataset file from the cache, and check the line count, the dollars and the flagged lines
