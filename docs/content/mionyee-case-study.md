# OwlClaw Case Study: Mionyee Trading System

> Status: Draft complete, waiting for real metrics attachment (`Task 3.2`).
> Data policy: no fabricated numbers. All quantitative claims must come from exported CSV files.

## Background

- System scope: Mionyee production workflow with governance overlay and scheduler migration.
- Core pain points before rollout:
  - LLM usage could spike without stable budget/rate guardrails.
  - Scheduler resilience risk in process restart and recovery windows.
- Business requirement:
  - Keep existing business behavior while adding governance visibility, resilience, and auditability.

## Solution

- Governance overlay (`mionyee-governance-overlay`):
  - Budget limit, rate-limit, and circuit-breaker policy around LLM invocation path.
  - Unified execution audit through Ledger records.
- Scheduler migration (`mionyee-hatchet-migration`):
  - APScheduler task set migrated to Hatchet durable execution model.
  - Recovery and retry semantics moved to persistent workflow layer.

## Implementation

- Scope of change:
  - Existing Mionyee business handlers kept; integration wrapped by OwlClaw governance/runtime boundaries.
  - Data collection tooling prepared for reproducible before/after evidence:
    - `scripts/content/verify_mionyee_case_inputs.py`
    - `scripts/content/collect_mionyee_case_data.py`
    - `docs/content/mionyee-data-collection-guide.md`
    - `docs/content/mionyee-data-export-checklist.md`
- Delivery path:
  - Step 1: export real CSV files from Mionyee source systems.
  - Step 2: run input verification and report generation scripts.
  - Step 3: attach generated `mionyee-case-data.md` and `mionyee-case-data.json` to this case file.

## Results

This section is intentionally metric-free until real data is attached.

- Required metrics (to be filled from `mionyee-case-data.md`):
  - Governance before/after: cost, call volume, intercepted count.
  - Scheduler before/after: success rate, recovery time.
- Evidence files expected:
  - `docs/content/mionyee-case-data.md`
  - `docs/content/mionyee-case-data.json`

## Reuse Validation

This case material is structured to support two downstream scenarios.

1. Technical article source (content channel)
   - Feeds the "Problem -> Solution -> Results" sections in:
     - `docs/content/first-article-draft-en.md`
     - `docs/content/first-article-draft-zh.md`
2. Consulting attachment (delivery channel)
   - Reused as proof section in:
     - `docs/consulting/ai-transformation-template.md`
     - `docs/consulting/scenario-report-insight.md`
     - `docs/consulting/scenario-customer-followup.md`
     - `docs/consulting/scenario-inventory-alert.md`

## Data Authenticity Statement

- No synthetic values are used in this case study.
- Any numeric claim must be traceable to raw exported CSV files and validation output.
