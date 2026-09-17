---
title: "Stage 1 counts must be exact, never from statistics"
date: 2026-09-09
type: decision
status: decided
project: table-recon
tags: [decision]
---

## Context

Stage 1 gates everything downstream on whether two record counts are equal. There
are cheap ways to get a row count: Hive `SHOW PARTITIONS` with
`TBLPROPERTIES.numRows`, or Oracle `USER_TAB_PARTITIONS.NUM_ROWS`. They return
instantly.

## Decision

Always `SELECT <date_col>, COUNT(*) GROUP BY <date_col>`. Never use catalog
statistics as the gate.

## Why

The gate is an equality test. Catalog statistics are collected on a schedule and
go stale between collections. A stale count produces either a false `count_diff`,
which sends someone chasing a difference that does not exist, or a false `match`,
which lets genuinely mismatched data into stage 2 where it quietly poisons the
comparison.

An exact `GROUP BY` on a single column is metadata-level or a single-column scan.
Compared to the stage 2 data download it is cheap, and it is the only number the
gate can be built on.

## Consequences

- csv and sas left sides have no query engine, so exact counts mean reading files.
  For sas this is the most expensive part of stage 1; where one file maps to one
  partition, use file metadata and avoid reading rows at all.
- Count the right side first. It is always one cheap query and it settles which
  partitions the right side lacks, which then bounds the left-side count with
  `date IN (...)` and prunes partitions that would only ever be `left_only`.
- `date_synonyms` (folding sentinel dates such as `3000-01-01`) must be applied to
  both sides **before** reconciling.
