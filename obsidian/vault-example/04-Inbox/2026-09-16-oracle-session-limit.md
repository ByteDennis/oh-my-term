---
title: "Oracle session limit during month-end"
date: 2026-09-16
type: inbox
tags: [inbox]
---

Overheard in the platform channel: month-end batch already saturates the Oracle
session pool, and another team had a job killed last month for holding two
sessions during the window.

We plan to hold two sessions for stage 1 counting on the two large pairs. If
month-end is the wrong time to be doing that, the scheduling assumption in
[[scheduling-five-pairs]] needs revisiting, or runs need to avoid the window.

Not sure yet whether this belongs to [[01-Projects/table-recon/_index|table-recon]] or
[[01-Projects/month-end-regulatory-extract/_index|month-end-regulatory-extract]]. Triage later.
