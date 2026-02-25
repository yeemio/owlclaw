---
name: morning-decision
description: Generate a morning trading plan before market open.
metadata:
  author: owlclaw-examples
  version: "1.0.0"
owlclaw:
  spec_version: "1.0"
  task_type: planning
  trigger: cron("0 9 * * 1-5")
---

# Morning Decision

Builds a priority plan from overnight context and risk constraints.

