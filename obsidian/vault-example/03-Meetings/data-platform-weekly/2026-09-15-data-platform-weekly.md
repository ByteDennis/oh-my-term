---
title: "Data platform weekly"
date: 2026-09-15
type: meeting
series: data-platform-weekly
attendees: [data platform lead, two platform engineers, me]
projects: ["[[01-Projects/table-recon/_index]]"]
tags: [meeting]
---

# Data platform weekly

## Prep

- Get an answer on whether detail rows may leave on-prem (`--upload-raw`). I have
  been assuming no and designing around it, but the cloud-side drill-down depends
  on it.
- Ask whether the Oracle session budget of 2 is fixed.
- Flag that stage 1 sits on the critical path so people are not surprised when a
  run's wall-clock time is dominated by counting.

## Notes

- Walked through the two-stage design. The barrier was questioned on the grounds
  that it would leave the cluster idle; explained that stage 1 runs on serverless
  and the cluster does not start until the first pair clears. That landed.
- Platform lead's view on `--upload-raw`: probably fine for aggregate statistics,
  needs a review for detail rows, and they do not want to be the one to decide.
  Suggested I write it up as a one-page question and send it to risk.
- Oracle sessions: the budget of 2 is a shared constraint, not specific to us.
  Raising it during month-end is possible in principle but needs a request with a
  window and a reason.
- One engineer pointed out that our report bucket is readable by a team outside
  the workspace, and asked whether `latest/` could be read mid-update. Confirmed
  that only `pointer.json` is overwritten, atomically.

## Decisions

- Aggregate statistics may leave on-prem. Detail rows are deferred pending a
  written question to risk.

## Action Items

- [ ] me - write the one-page `--upload-raw` question for risk - due 2026-09-19
- [ ] me - submit an Oracle session request for the month-end window - due 2026-09-22
- [ ] platform lead - confirm who signs off on the risk question
