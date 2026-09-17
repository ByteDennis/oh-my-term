---
title: "Quick reference"
date: 2026-09-15
type: reference
project: table-recon
tags: [reference]
---

# Quick reference

## Where things are

```
work bucket    s3://example-work/recon/v1/runs/{run_id}/
               _PREFLIGHT.json     health check
               _STATUS.json        where it is and what broke, look here first
               _HEARTBEAT          is the producer alive
               stage1/{pair}.json  every partition's verdict, for people
               manifest/{pair}.json  only passing partitions, for machines
               manifest/_CLOSED    producer says "done, N units total"
               _INDEX/{seq}-{unit_id}.json   ready pointers, all the consumer scans
               units/ raw/ results/ dead/

report bucket  s3://example-report/
               latest/pointer.json      the dashboard's only entry point
               history/{run_id}/...     immutable archive
```

## Three commands

```bash
recon s3-stage1 ... --gate auto --kickstart   # count, reconcile, fire, push
recon s3-status ... --run-id latest           # where is it
recon s3-push   ... --run-id <id> --stage2    # manual release under --gate manual
```

## Six rules

1. Throttle stage 1 concurrency **per left source**, not with one global number.
2. The **first** pair through the barrier fires the kickstart; do not wait for all.
3. Stage 1 smallest first (fire early), stage 2 largest first (finish early).
   Deliberately opposite.
4. Dispatch stage 2 units **rotating across pairs**, never one table at a time.
5. Reserve one worker for class A compares; class B takes at most `W-1`.
6. Hitting `--wip` means add cloud workers. High `idle_ratio` means remove some.

## Two places this goes wrong

1. **The `WHERE` clause for a window with holes.** If partitions excluded by
   stage 1 get pulled back in during the right-side fetch, results come out
   unequal for reasons that are very hard to trace. Needs a unit test.
2. **Overwriting `latest/` file by file.** The dashboard will read a half-updated
   run. Only `pointer.json` may be overwritten, and atomically.

## The one iron rule

> Unequal counts and unequal stats are **findings**: they go in the report and do
> not alert.
> Unreachable, timed out, crashed are **errors**: they alert and someone fixes
> them.
> Never mix the two, or the alerts will ring until nobody reads them.
