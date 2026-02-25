---
name: entry-monitor
description: Evaluate entry opportunities for watchlist symbols
metadata:
  author: mionyee-example
  version: "1.0.0"
  tags: [trading, monitoring]
owlclaw:
  spec_version: "1.0"
  task_type: trading_decision
  constraints:
    trading_hours_only: true
    cooldown_seconds: 300
---

# Entry Monitor

Use this skill to evaluate whether symbols meet entry criteria and to summarize actionable signals.
