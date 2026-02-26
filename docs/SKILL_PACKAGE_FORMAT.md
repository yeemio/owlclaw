# Skill Package Format

`package.yaml` defines a reusable OwlClaw skill bundle for team distribution.

## Required fields

```yaml
name: retail-skills
version: 1.0.0
industry: retail
description: Retail operations starter package
skills:
  - inventory-alert
  - order-anomaly
requires:
  owlclaw: ">=1.0.0"
```

- `name`: package id, kebab-case recommended.
- `version`: package version, semantic version recommended.
- `industry`: target industry label (for discovery/filtering).
- `description`: short package summary.
- `skills`: non-empty list of OwlHub skill names.
- `requires.owlclaw`: minimum OwlClaw version expectation.

## Install

```bash
owlclaw skill install --package ./package.yaml
```

The installer reads `skills` and installs each listed skill via OwlHub index/API.

## Validation expectations

- Package file must be valid YAML mapping.
- `skills` must be a non-empty list of skill name strings.
- Unknown fields are allowed for forward compatibility.
