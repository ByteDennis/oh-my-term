# vault-example

A filled-in vault you can open in Obsidian to see what the structure feels like
before committing to it. Every note here is example content.

The worked example is a table reconciliation pipeline, written the way a data
analyst at a bank would actually accumulate notes: decisions recorded the day they
were made, one file per meeting, two reports a week, one reflection.

```
00-Home.md            landing page
Todo.md               one shared task surface
01-Projects/          permanent domains, one folder each
02-Reports/           twice a week
03-Meetings/          one file per meeting, recurring series get a folder
04-Inbox/             capture first, triage later
05-People/
06-Clippings/
07-Reflection/        weekly, five minutes
```

Things worth looking at specifically:

- `01-Projects/table-recon/` shows the shape a real project takes: a short
  `_index.md`, eight notes, four decisions, one reference sheet. Note how little
  of it is in the index.
- `decisions/` shows why decisions are separate files. Read
  `2026-09-08-two-stage-barrier.md` and then look at how `_index.md` links to it
  in one line.
- `02-Reports/2026-W38-2.md` is assembled from the week's material rather than
  written from memory. The `Evidence` section is the raw input, not for the reader.
- `07-Reflection/2026-W38.md` is honest about a gap. That is the only way the
  reflection loop is worth anything.

To start your own vault from the structure without the example content:

```bash
../scripts/init-vault.sh /path/to/your/vault
```

See `../docs/first-week.md`.
