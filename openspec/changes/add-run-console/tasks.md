## 1. CLI

- [ ] 1.1 Scaffold Typer app and command groups
- [ ] 1.2 Implement exit-code mapping and error messages

## 2. Orchestration

- [ ] 2.1 Implement stage graph runner with manifest-first guard
- [ ] 2.2 Implement checkpoints and `--resume`
- [ ] 2.3 Implement time and cost budget enforcement with `budget_exhausted` Review rows
- [ ] 2.4 Emit stage action telemetry
- [ ] 2.5 Implement `--set train|validation` for development runs, and refuse a run on all rows until TEST is sealed

## 3. Rerun and acceptance

- [ ] 3.1 Implement `itemizer rerun` with identical-output check
- [ ] 3.2 Add 1,500-row timing benchmark for the D4 check in add-delivery-acceptance
- [ ] 3.3 Tests per scenario in `run-console`
