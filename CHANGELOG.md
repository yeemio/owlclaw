# Changelog

All notable changes to this project are documented in this file.

## [0.1.0] - 2026-02-25

### Added
- Core OwlClaw runtime, skills registry, trigger framework, governance, and memory subsystem.
- CLI toolchain (`owlclaw db`, `owlclaw skill`, `owlclaw scan`, `owlclaw migrate`, `owlclaw release gate`).
- Declarative binding generation and validation flow.
- OwlHub index/site/release-gate related modules and tests.
- Example suite including cron/langchain/binding/mionyee flows and smoke validation.

### Changed
- Normalized multiple spec documents to align `spec -> code -> tests -> docs`.
- Added release-oriented CI tasks and workflow improvements.

### Notes
- External release execution (PyPI publish, GitHub Discussions/public settings) depends on repository permissions and credentials.

