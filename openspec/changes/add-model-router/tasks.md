## 1. Interface

- [ ] 1.1 Define `PromptRequest`, `ProviderResponse`, `Provider` protocol
- [ ] 1.2 Write provider contract tests (schema output, timeout, error mapping)

## 2. Adapters

- [ ] 2.1 Implement Ollama local adapter with digest pinning
- [ ] 2.2 Implement external API adapter with structured output, retries, rate limits
- [ ] 2.3 Implement rules-only null provider

## 3. Policy and gate

- [ ] 3.1 Implement routing policy with carrier/size overrides
- [ ] 3.2 Implement confidentiality gate with dataset class and approval checks, and PII re-scan
- [ ] 3.3 Implement fallback controller

## 4. Cache, cost, canary

- [ ] 4.1 Implement SQLite response cache with model-scoped keys
- [ ] 4.2 Implement cost meter with price table lookup
- [ ] 4.3 Implement canary replay and silent-change events
- [ ] 4.4 Emit action telemetry per call

## 5. Tests

- [ ] 5.1 Tests per scenario in `model-routing`
