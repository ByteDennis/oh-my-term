---
title: "Reconciliation scope review"
date: 2026-09-11
type: meeting
series: ""
attendees: [reporting lead, me]
projects: ["[[01-Projects/table-recon/_index]]"]
tags: [meeting]
---

# Reconciliation scope review

## Prep

- Confirm which five tables are in scope for the first production run.
- Establish what "done" means for a run: is a partial report acceptable?

## Notes

- Five pairs confirmed: account, transaction, customer, product reference, balance
  history. Transaction is by far the largest and will dominate wall-clock time.
- Reporting lead's main question was not about accuracy but about **repeatability**:
  can the same run be re-run and produce the same answer. Explained the `run_id`
  and idempotency design.
- On partial results: a `PARTIAL` report is acceptable and preferred over nothing,
  provided the report states clearly which columns were not compared. Explicitly
  not acceptable is a report that omits a failed column silently.
- Asked about sampling confidence. Made the point that sampling establishes that a
  difference exists and does not itself draw the conclusion; every finding ships
  with a full-population confirmation query. That was the answer they wanted.

## Decisions

- Five pairs in scope for the first production run.
- `PARTIAL` reports are acceptable when the uncompared columns are named.

## Action Items

- [ ] me - make sure `dead/` units appear by name in the report, not just as a count
- [ ] me - include the confirmation SQL inline in the per-pair html
