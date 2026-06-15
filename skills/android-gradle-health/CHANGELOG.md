# Changelog

All notable changes to this plugin follow [Semantic Versioning](https://semver.org).

## 1.0.0 — 2026-06-14

### Added
- Official plugin structure with `.claude-plugin/plugin.json` manifest
- Skill available as `/android-gradle-health:android-gradle-health`
- **Option B: temporary env without installation** — `pipx run --spec "android-gradle-analyzer>=1.4.0"` prefix
  lets users run all commands in an isolated temporary Python environment without a permanent install
- Plugin-level `README.md` and `CHANGELOG.md`

### Changed (from skill-only to plugin)
- Skill rewritten in English with full JSON output schemas for all four commands
- Commands now documented with `--json --quiet` flags (clean, parseable output)
- `--quiet` flag added to all command examples (suppresses progress output)
- Prerequisite section restructured into Option A (permanent) and Option B (temporary)
- Command table updated: shows what each command returns and when to use it
- Extraction engine table (`static` / `dynamic` / `auto`) improved with clearer guidance
- Score interpretation table updated to English
- References table cleaned up: removed `ci-cd.md` and `interpret-sanity.md`
  (those guides were removed upstream as their content was consolidated)
- `examples/` configs updated to reflect current `analyzer_config.json` schema

### Removed
- `references/ci-cd.md` — removed upstream (CI/CD guidance consolidated elsewhere)
- `references/interpret-sanity.md` — removed upstream (JSON schema now in SKILL.md directly)
