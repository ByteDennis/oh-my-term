# Building on the two reference vaults

Two public vaults are worth studying. They teach different things and neither is
meant to be copied whole.

## xupisco/obsidian-sample-vault — the tool layer

308 files, almost no real notes: 49 plugins, ~35 CSS snippets, 10 Bases
dashboards. It is a configuration showcase.

Worth taking:

- **One CSS snippet per plugin**, named `plugin_<name>.css`. When the UI breaks,
  you disable one file and know which plugin did it. This repo already follows it.
- **`_index.md` folder notes** so every folder has a landing page.
- **Bases dashboards** instead of hand-written queries. Read
  `Assorted/Bases/Tasks - Reloaded.base` and `Vault monitor.base` first.
- **Number-prefixed folders** so sidebar order is fixed and meaningful.

Not worth taking: the 49 plugins, the fake client data, and the committed vector
database. On a 16 GB machine the plugin count is the part that will actually hurt.

## lukeinglis/work-vault — the method layer

An Obsidian vault driven by Claude Code: folder taxonomy, 13 templates, 13 slash
commands, MCP integrations.

Read `docs/philosophy.md` first. It is the most useful file in either repo.

Worth taking:

- **The inbox pattern.** Capture friction is the thing that kills these systems.
- **Decision logging.** "Decisions are more valuable than specs. Specs describe
  what you are building. Decisions describe why. Decisions age well; specs don't."
- **One file per meeting**, with all sources consolidated into it.
- **Instructions inside the template**, in an HTML comment. This is the one to
  internalise; see below.

To adapt: their `01-Components/` is a product-management idea. For engineering
work the equivalent permanent domain is a repo or a service, which is why this
repo calls it `01-Projects/`.

To defer: everything under `.claude/`, the MCP servers, and the pull scripts.
They need Claude Code.

## What neither has

Twice-weekly reporting and a reflection loop. Those are in `templates/report.md`
and `templates/reflection.md`, and they are the reason this vault exists at all.
Everything else is in service of having the inputs ready when the report is due.

## Designing for automation you do not have yet

Claude Code may become available later. Five habits make it a drop-in rather than
a rewrite:

1. Plain markdown for anything that matters. Canvas and Excalidraw for sketches,
   never for a decision record.
2. YAML frontmatter on every note. It is the first thing a machine reads.
3. Stable, number-prefixed folder names. Renaming later breaks every link.
4. One thing per file. One meeting, one decision, one clipping.
5. Put the instructions **in the template**, in an HTML comment.

Point 5 is the whole trick. Today that comment is a note to yourself about how to
fill the file in. The day an assistant can read the vault, it is already a working
instruction and you change nothing. That is why lukeinglis's vault works: the
structure came first and the automation came second.
