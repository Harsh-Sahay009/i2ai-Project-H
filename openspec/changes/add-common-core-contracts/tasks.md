## 1. Package setup

- [ ] 1.1 Create `itemizer/core` package with `pyproject.toml` entry managed by uv
- [ ] 1.2 Add pydantic v2 and configure strict mode and Decimal handling

## 2. Contracts

- [ ] 2.1 Implement `DisputeRow`, `Note`, `ChargeItem`, `RowResult`, `RowOutcome`, `CaseId` models with `contract_version`
- [ ] 2.2 Generate JSON Schemas into `contracts/schemas/` and add a test that fails when they drift
- [ ] 2.3 Write fixtures: 20 annotated sample notes covering single, multi, rate×quantity, tax, already-paid, no-charge

## 3. Invariants

- [ ] 3.1 Implement evidence verbatim validator with `exact` and `exact_ws_normalized` modes
- [ ] 3.2 Implement amount-in-evidence and rate×quantity product check
- [ ] 3.3 Implement no-edit validator
- [ ] 3.4 Unit tests per scenario in `item-schema-contract`

## 4. Run manifest

- [ ] 4.1 Implement `RunManifest` model and canonical JSON serializer
- [ ] 4.2 Implement `run_id` derivation and completeness check
- [ ] 4.3 Implement Git SHA / lockfile / dirty-tree capture and prod guard
- [ ] 4.4 Unit tests per scenario in `run-manifest`

## 5. Contract test harness

- [ ] 5.1 Implement `pytest -m contract` harness parametrized over registered itemizer implementations
