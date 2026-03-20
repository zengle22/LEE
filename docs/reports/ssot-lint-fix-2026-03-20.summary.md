# SSOT Lint Fix Summary (2026-03-20)

- Command: `lee ssot lint`
- Result: `passed`
- Strategy: fixed deterministic issues first, then deprecated unfixable or legacy-invalid files.
- Deprecated file count: **286**
- Deprecated root: `legacy/deprecated-ssot/2026-03-20`
- Full deprecated list: `docs/reports/ssot-lint-fix-2026-03-20.deprecated-files.json`

## Verification
- `lee ssot lint` -> pass
- `lee ssot validate` -> pass
- `lee ssot rebuild-registry` -> 119 artifacts
