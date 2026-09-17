# The first week

Run the system by hand before automating anything. At the end of the week you
will know which parts you actually use, and you delete the rest. Four templates
you use beat thirteen you do not.

## Setup (about an hour)

```bash
./scripts/init-vault.sh /c/Users/<you>/vault
```

Then in Obsidian: open the folder as a vault, install the four plugins listed in
`dot-obsidian/community-plugins.json`, point Templater at `Templates/`, and point
Homepage Studio at `00-Home.md`.

Nothing else. Resist the urge to install more.

## The daily loop

**Capture.** Anything you are unsure about goes to `04-Inbox/`. Do not decide
where it belongs at capture time; that decision is what makes people stop
capturing.

**Meetings.** One file per meeting, in `03-Meetings/`. Recurring meetings get
their own folder so the history is scannable. Fill in `## Prep` before, not after.

**Decisions.** The moment you catch yourself explaining why something is the way
it is, that is a decision. Write it in the project's `decisions/` folder, same
day. A decision written a week later is a reconstruction.

**Triage.** Once a day, empty `04-Inbox/`. Every item moves somewhere or gets
deleted. Deleting is a valid outcome and most items deserve it.

## Twice a week

Write the report. It should be assembled, not remembered:

```bash
just -g report-commits "3 days ago"
```

Paste that under `## Evidence`, skim the meetings and decisions since the last
report, then write the four sections. Fifteen minutes.

If it takes an hour, the problem is not the template. It means the week was not
captured as it happened, and that is what to fix.

## Once a week

Right after the second report, write the reflection. Five minutes, three bullets
per section. It feels pointless the first three times. The value shows up when
you read a month of them in one sitting and notice the same gap in all four.

## At the end of the week

Delete what you did not use. Unused folders and templates make the vault feel
like homework, and a vault that feels like homework gets abandoned.
