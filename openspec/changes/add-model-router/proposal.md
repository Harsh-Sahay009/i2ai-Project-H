## Why

We own no model, yet we must decide which model handles each note, keep any data not cleared for outside use away from outside providers, survive a provider outage, keep reruns reproducible and know what each run costs. The atlas puts this orchestration in the controlled layer: own the routing even when renting the model, and keep a tested exit path.

## What Changes

- Add a Provider Interface with contract tests and two adapters: Local Model (Ollama) and External API.
- Add a Routing Policy Engine (rules-only, local, external, external-then-local) with per-carrier/size overrides.
- Add a fail-closed Confidentiality Gate (anonymized dataset with a recorded source, or approval flag + approval reference).
- Add a Fallback Controller, a content-hash Response Cache and a Cost Meter.
- Add canary fingerprints for silent upstream model change detection.

## Capabilities

### New Capabilities
- `model-routing`: provider abstraction, routing policy, confidentiality gate, fallback, caching, cost metering, drift canary.

### Modified Capabilities
<!-- none -->

## Impact

- New package `itemizer.router`; SQLite cache under `${runtime.data_root}/cache`.
- Depends on configuration registry (routing family), telemetry store, core contracts.
- External dependency: external LLM SDK; Ollama locally as the fallback.
