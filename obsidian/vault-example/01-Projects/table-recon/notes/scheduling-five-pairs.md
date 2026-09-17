---
title: "Scheduling five pairs at once"
date: 2026-09-14
type: note
project: table-recon
tags: [note, scheduling]
---

# Scheduling five pairs at once

| | pair | left | right | size |
|---|---|---|---|---|
| P1 | `acct` | oracle | `main.core.account_daily` | large |
| P2 | `txn` | oracle | `main.core.txn_daily` | very large |
| P3 | `customer` | hadoop | `main.core.customer_master` | medium |
| P4 | `product_ref` | csv | `main.ref.product` | small |
| P5 | `balance_hist` | sas | `main.core.balance_history` | medium |

Five different left sources, one right side. That asymmetry is deliberate.

## Rule 1: limit stage 1 concurrency per left source, not globally

This is the easiest thing to get wrong. Writing `--pair-workers 5` sends all five
at once, and P1 and P2 both ask Oracle for a session at the same time. Together
with everyone else's jobs, the DBA comes looking for you.

One gate per source instead:

```jsonc
"source_limits": {
  "oracle": 2,      // we are only allowed 2 sessions
  "hadoop": 1,      // shared cluster, be polite
  "csv":    4,      // local disk, no limit worth setting
  "sas":    2,      // local CPU, reading files is memory hungry
  "databricks": 8   // the counting warehouse can take it
}
```

So P1 and P2 take Oracle's two slots, P3 has hadoop to itself, P4 and P5 run
locally. **All five pairs really do run stage 1 in parallel**, each throttled by
its own source.

Right-side counting is exempt: five `GROUP BY` queries hit the same serverless
warehouse, which queues them itself and returns everything within 12 seconds.

## Rule 2: whoever clears the barrier first fires the kickstart

```
00:03  all five pass preflight
00:15  all five right-side counts are back
00:23  P4 (csv, small) reconciles -> GATE_PASSED -> kickstart
00:35  P5 (sas) clears
01:00  P3 (hadoop) clears
02:15  P1 (oracle) clears
05:10  P2 (oracle, very large) clears, last
```

**The cluster starts at 00:23, not 05:10.** During the four minutes it takes to
boot, P1 and P2 are still counting Oracle while P4, P5 and P3 are already pushing
units. The cluster opens its eyes to a pile of waiting work.

This is exactly why the manifest must be one file per pair. A single combined file
could only be written once every pair had cleared, which would push the kickstart
to 05:10 and throw away four and a half minutes.

## Rule 3: the two stages sort in opposite directions

Counter-intuitive, but it follows directly:

- **Stage 1: smallest first.** The point is to clear *someone* as early as
  possible so the cluster starts booting.
- **Stage 2: largest first.** The point is to finish; the longest pole should
  start earliest.

## Rule 4: rotate across pairs when dispatching units

Never finish one table before starting the next. See
[[2026-09-10-round-robin-dispatch]].

## Rule 5: reserve one worker for class A

Class B prefetch may occupy at most `W-1` workers. Without the reservation, a
burst of prefetch starves the compares that actually produce results.

## Rule 6: the producer has a brake

Hitting `--wip` means the cloud side is short, so add workers. A high
`idle_ratio` means there are too many, so remove some.

## Full timeline, five pairs

```
time    local PC                         Databricks
---------------------------------------------------------------
00:00   run_id generated
00:03   5 preflights pass                serverless warehouse
00:15   5 right-side counts back         serverless warehouse
00:15   left counts begin:
          csv P4 / sas P5 local
          hadoop P3 one slot
          oracle P1,P2 two slots
00:23   P4 clears, KICKSTART             cluster QUEUED
00:23   P4 pushes units (small, 30s)     cluster STARTING
00:35   P5 clears, pushes
01:00   P3 clears, pushes
02:15   P1 clears, pushes (large first)
04:30                                    cluster RUNNING
04:30                                    reads 4 manifests
04:30                                    queue A already has P4/P5 units, compares
04:31                                    queue B loads right-side windows
05:10   P2 clears, pushes
...     P1/P2 rotate pushing units       A first, B when A is empty
18:40   last unit pushed
18:41   manifest/_CLOSED {expected_units: 640}
...                                      keeps draining
19:05                                    640/640 + _CLOSED -> finalize
19:30                                    3 Delta tables + 5 index.html
19:40                                    report bucket ready, alert sent
```

19 minutes 40 seconds for five tables. Run serially, one table after another, it
would be about 55 minutes.

## Related

- [[producer-design]]
- [[consumer-design]]
