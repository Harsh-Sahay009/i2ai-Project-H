## 1. Store

- [ ] 1.1 Implement CAS write/read with sidecar metadata and immutability check
- [ ] 1.2 Refuse a `runtime.data_root` that Git does not ignore

## 2. Index

- [ ] 2.1 Create DuckDB tables `artifacts`, `lineage`, `access_log`
- [ ] 2.2 Implement lineage query and `itemizer lineage`

## 3. Git-tagged artifacts

- [ ] 3.1 Implement registration by tag/commit/content hash with moved-tag detection

## 4. Access control and restoration

- [ ] 4.1 Implement sealed-set role check and access logging
- [ ] 4.2 Implement manifest-driven restore for `itemizer rerun`

## 5. Tests

- [ ] 5.1 Unit tests per scenario in `version-registry`
