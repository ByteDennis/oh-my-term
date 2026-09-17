---
title: "S3 strong read-after-write and LIST consistency"
date: 2026-09-09
type: clipping
source: "AWS S3 documentation, consistency model"
tags: [clipping]
---

## Why I saved this

The whole commit protocol in [[s3-layout-and-commit-protocol]] rests on this. If
LIST were still eventually consistent, the consumer could see an `_INDEX` entry
whose data object is not yet visible, and the "write data then write pointer"
ordering would not be sufficient.

## Notes

- Since December 2020, S3 provides strong read-after-write consistency for PUT and
  DELETE of objects, **including list operations**. No extra configuration, no
  performance or cost difference.
- A single object PUT is atomic. There is no state in which a reader sees a
  partially written object.
- This is what makes the pattern safe: write the data object, then write the
  pointer object. A reader that only ever scans pointers cannot observe a torn
  write.
- It does **not** make multi-object updates atomic. That is why `latest/` in the
  report bucket must be a single `pointer.json`, not a set of files updated one by
  one.
