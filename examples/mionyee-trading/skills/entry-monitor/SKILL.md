---
name: entry-monitor
description: Monitor entry opportunities for owned symbols.
metadata:
  author: owlclaw-examples
  version: "1.0.0"
owlclaw:
  spec_version: "1.0"
  task_type: trading_decision
  trigger: cron("*/5 * * * *")
---

# Entry Monitor

Checks signal conditions for candidate entries and returns structured alerts.

