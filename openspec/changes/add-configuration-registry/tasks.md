## 1. Schema

- [ ] 1.1 Write `config/schema/parameters.schema.json` with every key from the parameter catalog and its metadata
- [ ] 1.2 Generate typed pydantic settings models from the schema

## 2. Resolver

- [ ] 2.1 Implement layered loader (core, env, carrier, CLI) with per-key override permissions
- [ ] 2.2 Implement limit validation without clamping and unknown-key suggestions
- [ ] 2.3 Implement freezing, canonical JSON and config hash
- [ ] 2.4 Implement per-row carrier override lookup API

## 3. Gates and log

- [ ] 3.1 Implement gate checks (promotion reference, written approval, locked)
- [ ] 3.2 Implement change log from Git history plus `config/CHANGELOG.yaml` entries
- [ ] 3.3 Implement `itemizer config show|history|expired|validate`
- [ ] 3.4 Add CI job running `itemizer config validate`

## 4. Defaults

- [ ] 4.1 Write `config/core/defaults.yaml`, `config/env/dev.yaml`, `config/env/prod.yaml`
- [ ] 4.2 Unit tests per scenario in `configuration-registry`
