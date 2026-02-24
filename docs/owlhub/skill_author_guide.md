# OwlHub Skill Author Guide

## Package Layout

```
<publisher>/<skill-name>/
  SKILL.md
```

## Minimal SKILL.md

```markdown
---
name: "entry-monitor"
publisher: "acme"
description: "Monitor entry signals"
license: "MIT"
tags: [monitoring, trading]
dependencies: {}
metadata:
  version: "1.0.0"
---
```

## Local Validation

```bash
owlclaw skill validate ./my-skill --strict
```

## Publish Checklist

1. Ensure `name/publisher/version/description/license` are present.
2. Provide a stable package URL and checksum when publishing remote artifacts.
3. Keep version semver-compatible.
4. Track review result via returned `review_id`.
