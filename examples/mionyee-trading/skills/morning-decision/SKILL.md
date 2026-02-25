---
name: morning-decision
description: Build start-of-day execution priority for the trading session
metadata:
  author: mionyee-example
  version: "1.0.0"
  tags: [trading, planning]
owlclaw:
  spec_version: "1.0"
  task_type: planning
  trigger: cron("0 9 * * 1-5")
---

# Morning Decision

Use this skill to determine the first operational actions at market open based on current state and constraints.
