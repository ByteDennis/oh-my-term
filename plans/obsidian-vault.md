# Obsidian Work Vault — Learning Plan

> Goal: learn from two public vaults, then build your own.
> Written simple on purpose. The point is to teach you **how to do it** and
> **how to build on top of them**, not to hand you a finished vault.

**Your starting point**

| Item | Status |
|---|---|
| Obsidian | installed, Windows 64, company laptop |
| Plugins | only **Homepage Studio** |
| Vault upload | ❌ **not allowed** — company content must never leave the machine |
| Claude Code | ❌ not available yet, **may come later** |
| Your work | engineering / code, meetings / collaboration, personal knowledge + clipping |
| Your rhythm | **report progress twice a week**, and reflect on progress and gaps continuously |
| Hardware | **16 GB RAM**, not a powerful machine — see §5.1 for the memory budget |

That last row matters most. Neither reference vault does reporting or reflection.
You will have to build that part yourself. This plan shows you how.

---

## 1. What each vault is actually for

They look similar but they teach completely different things.

### 1.1 xupisco/obsidian-sample-vault — the **tool layer**

308 files, but almost no real notes. What is inside:

- **49 community plugins** (bundled in the repo, so you can read their settings)
- **~35 CSS snippets**, one per plugin (`plugin_dataview.css`, `plugin_kanban.css`, ...)
  plus `.scss` sources — this is a **build pipeline for vault styling**
- **10 `.base` files** — Obsidian Bases dashboards (Tasks, People, Project Notes, Vault monitor)
- A tiny fake dataset: `03_Clients/ACME/`, `Assorted/People/@John Doe.md`, `Daily/2026/06/`
- `z_templates/` — 7 templates (`_daily`, `_call`, `_task`, `_people`, `_project-index`, ...)

**What this vault really is: a configuration showcase.** The notes are fake.
The value is the setup.

| Copy this | Skip this |
|---|---|
| One CSS snippet **per plugin**, named `plugin_<name>.css`. Easy to toggle one off when something breaks. | Installing 49 plugins. See §5. |
| `_index - <Folder>.md` folder-note pattern — every folder has a landing page | The `.smart-env/` AI embedding cache — that is a plugin artifact, not a design |
| `z_templates/` with `z_` prefix so templates sort to the bottom | The fake ACME/client data |
| `.base` dashboards instead of hand-written Dataview queries | `AI/YOLO/.yolo_vector_db.tar.gz` — do not commit binaries into a vault |
| Number-prefixed folders (`01_Docs`, `02_Management`, `03_Clients`) | |

### 1.2 lukeinglis/work-vault — the **method layer**

Described by its author as "An AI-powered work vault built on Obsidian + Claude Code".
What is inside:

- **Folder taxonomy**: `01-Components/`, `02-Weekly/`, `03-Meetings/`, `04-Inbox/`,
  `05-People/`, `06-Presentations/`, `07-Usage/`, `99-Archive/`
- **13 templates** — meeting, decision, research, one-pager, person, initiative-overview,
  spec-draft, weekly, skill
- **13 Claude Code slash commands** — `/prep-day`, `/close-day`, `/decision`,
  `/research`, `/pull-emails`, `/pull-slack`, `/jira-vault-sync`, ...
- **`.claude/rules/`** — path-scoped rules that load automatically
  (inbox-triage, meeting-workflow, todo-management, weekly-workflow)
- **`docs/philosophy.md`** — the reasoning behind every structural choice

**Read `docs/philosophy.md` first.** It is the single most useful file in either repo.

Five ideas worth stealing:

1. **Components vs Initiatives.** Components are permanent domains that never end.
   Initiatives are time-bound projects inside them. Context accumulates at the
   component level while initiatives come and go.
2. **The inbox pattern.** Everything enters `04-Inbox/` first. You often do not know
   where something belongs at capture time. Triage later, when you have focus.
3. **Decision logging.** "Decisions are more valuable than specs. Specs describe what
   you are building. Decisions describe why. Decisions age well; specs do not."
4. **Weekly scratch pad → distilled summary.** One messy file per week, then a curated
   10–20 bullet summary. Daily notes are too granular, monthly is too coarse.
5. **Templates carry instructions inside HTML comments.** Invisible when rendered,
   readable by both you and an AI later. This is the key CC-ready trick — see §3.2.

| Copy this | Adapt this | Defer this |
|---|---|---|
| Inbox pattern | `01-Components/` → `01-Projects/` (you do engineering, not product management) | Everything in `.claude/` |
| Decision logging | Weekly cadence → **twice-weekly**, because that is your reporting rhythm | `.mcp.json` and MCP servers |
| Meeting notes as one file per meeting | `Todo.md` ownership levels — keep the file, drop the `cc` owner for now | `scripts/` (email/Slack pulling) |
| HTML-comment instructions in templates | | |

### 1.3 How they fit together

```
   lukeinglis  →  structure, templates, workflows      (WHAT you write)
     xupisco   →  plugins, CSS, dashboards, navigation (HOW it looks and moves)
        you    →  reporting loop + reflection loop     (NEITHER vault has this)
```

You said "both in parallel", so this plan advances the tool layer and the method
layer together in every phase.

---

## 2. Two constraints that shape everything

### 2.1 The vault cannot be uploaded

Company content must never reach GitHub. So **split config from content physically**:

```
C:\Users\<you>\vault\          ← the REAL vault. Never a git repo. Never uploaded.
│
│   (config is copied in and out by a script)
│
oh-my-term repo, obsidian-vault branch
└── obsidian/
    ├── dot-obsidian/          ← .obsidian config: app.json, hotkeys.json, snippets/
    ├── templates/             ← template .md files (generic, no company names)
    ├── bases/                 ← .base dashboards
    └── docs/                  ← your own notes on how the system works
```

Rules:
- The repo holds **structure and settings only**. Never a real note.
- Before committing, check the diff. `.obsidian/workspace.json` records open file
  paths — those paths can leak project names. **Gitignore it.**
- Template files must use placeholders (`{{title}}`), never real project names.

```gitignore
# never commit these — they leak content or are machine-specific
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/plugins/*/data.json
.smart-env/
```

A small sync script keeps the two in sync (run it by hand, it is not automatic):

```bash
# >>> push config from the real vault into the repo <<< #
VAULT="/c/Users/$USER/vault"
REPO="$HOME/oh-my-term/obsidian"
rsync -a --delete \
  --exclude 'workspace*.json' --exclude 'plugins/*/data.json' \
  "$VAULT/.obsidian/" "$REPO/dot-obsidian/"
rsync -a "$VAULT/Templates/" "$REPO/templates/"
```

### 2.2 Claude Code is not available yet, but may be later

Do not wait for it, and do not design a system you will have to rewrite when it
arrives. Follow these five rules now and Claude Code becomes a drop-in later:

1. **Plain markdown only.** No plugin-locked formats for anything important.
   Canvas and Excalidraw are fine for sketches, never for the record of a decision.
2. **YAML frontmatter on every note.** This is what a machine reads first.
   ```yaml
   ---
   title: "Weekly sync"
   date: 2026-09-17
   type: meeting
   project: [inference-pipeline]
   people: [alice, bob]
   tags: [meeting]
   ---
   ```
3. **Stable, number-prefixed folder names.** `03-Meetings/` will still mean meetings
   in a year. Renaming folders later breaks every link and every future automation.
4. **One thing per file.** One meeting, one decision, one clipping.
   Never append today's meeting to yesterday's file.
5. **Put instructions inside the template**, in an HTML comment. Copy this pattern
   from lukeinglis — it is the whole CC-ready trick in one move:
   ```markdown
   <!--
   How to fill this in:
   - Prep is written BEFORE the meeting. Do not overwrite it afterwards.
   - Action items get copied to Todo.md with a link back to this file.
   - Write in bullets. No filler.
   -->
   ```
   Today that comment is a note to yourself. The day Claude Code shows up, it is a
   working instruction and you change nothing.

> **Why this matters**: lukeinglis's vault only works because the templates already
> tell the AI what to do. The structure came first, the automation came second.
> You are doing the same thing, just with a longer gap in between.

---

## 3. Your folder structure

Adapted from lukeinglis, reshaped for engineering + reporting + reflection:

```
00-Home.md                  ← Homepage Studio points here
01-Projects/                ← was "01-Components". Permanent, one per repo or workstream
  <project>/
    _index.md               ← folder note: what it is, status, links  (xupisco pattern)
    decisions/              ← why we did it this way                  (lukeinglis pattern)
    notes/                  ← working notes, debugging logs
    refs/                   ← links, papers, docs
02-Reports/                 ← ★ YOURS. Twice a week.
  _drafts/
  2026-W38-1.md
  2026-W38-2.md
03-Meetings/
  <recurring-series>/       ← one folder per recurring meeting, so history is scannable
  _one-off/
04-Inbox/                   ← everything lands here first
05-People/
  @alice.md
06-Clippings/               ← web clippings, papers, snippets
07-Reflection/              ← ★ YOURS. Progress and gaps.
  2026-W38.md
99-Archive/
Templates/
```

Two folders are marked ★ because neither reference vault has them. They exist
because of your rhythm: report twice a week, reflect continuously.

**Naming rules**
- Number prefixes so the sidebar order is fixed and meaningful.
- `_index.md` inside each project folder (needs the **Folder Notes** plugin to open
  when you click the folder).
- `@` prefix for people, so `@` in search jumps straight to a person.
- ISO weeks (`2026-W38`) everywhere. Sorts correctly, no ambiguity.

---

## 4. The two loops that matter most for you

This is the part you cannot copy from either repo. Build it yourself.

### 4.1 Report loop — twice a week

The problem: writing a progress report from memory takes an hour and misses things.
The fix: the report should be **assembled, not written**. Every input already exists
in the vault by the time you sit down.

Inputs that must already be there:
- meeting notes from `03-Meetings/` since the last report
- decisions from `01-Projects/*/decisions/`
- your own git commits (see the bridge below)
- open items from `Todo.md`

`Templates/report.md`:

```markdown
---
title: "Report {{date}}"
date: {{date}}
period: ""        # e.g. 2026-W38-1 (Mon-Wed) or 2026-W38-2 (Thu-Sun)
type: report
tags: [report]
---

<!--
Assemble, do not write from memory. Order of operations:
1. Skim 03-Meetings/ since the last report. Pull decisions and action items.
2. Skim 01-Projects/*/decisions/ for anything new.
3. Run the git bridge below and paste the commit list.
4. Only then write the summary. It should take 15 minutes, not an hour.
Keep it to bullets. Leadership reads the first three lines and stops.
-->

## Done
-

## In progress
-

## Blocked / needs a decision
-

## Next
-

## Evidence
<!-- raw material: commits, meeting links, decision links. Not for the reader. -->
```

**The git bridge.** Your commits are already a log of what you did. Turn them into
report material in one command. Put this in the global justfile from
[cross-platform-workbench.md](cross-platform-workbench.md):

```just
# >>> list my commits since a date, formatted for a vault report <<< #
[no-cd]
report-commits since="3 days ago":
    @git log --since="$1" --author="$(git config user.email)" \
        --pretty=format:'- %s  `%h`' --no-merges

# >>> same thing across every repo under a parent directory <<< #
[no-cd]
report-all since="3 days ago" root=".":
    #!/usr/bin/env bash
    set -euo pipefail
    for d in "$2"/*/.git; do
        repo=$(dirname "$d")
        out=$(git -C "$repo" log --since="$1" --author="$(git config user.email)" \
              --pretty=format:'- %s  `%h`' --no-merges)
        [ -n "$out" ] && printf '\n### %s\n%s\n' "$(basename "$repo")" "$out"
    done
```

> When Claude Code arrives, this whole section becomes a `/report` command.
> The template already says what to do — that is why §2.2 rule 5 mattered.

### 4.2 Reflection loop — progress and gaps

You asked for continuous reflection on progress and shortcomings. Keep it small or
you will stop doing it. **One file per week, five minutes, at the same time as the
second report of the week.**

`Templates/reflection.md`:

```markdown
---
title: "Reflection {{date}}"
date: {{date}}
type: reflection
tags: [reflection]
---

<!--
Five minutes. Three bullets each, no more. Honesty beats completeness.
Link to the evidence, do not re-explain it.
-->

## What moved
<!-- real progress, with a link to the proof -->
-

## What did not
<!-- be specific: what blocked it, was it you or the situation -->
-

## Gap I noticed
<!-- a skill, a habit, a knowledge hole. One is enough. -->
-

## One thing to try next week
-
```

**Homepage Studio does half of this for you already.** Its writing heatmap shows
which days you actually wrote, and its date-section journal (`## YYYY-MM-DD`) is a
good place for the raw daily line that feeds the weekly reflection. Point the plugin
at `00-Home.md` and put the current week's reflection in a curated file group.

Then a monthly review is just reading four reflection files. That is the payoff:
**the gaps repeat, and you only see the pattern when they are in one place.**

---

## 5. Plugin plan — staged, not all at once

xupisco runs 49 plugins. **Do not copy that.** A large plugin set slows startup,
breaks on updates, and hides the fact that you have not built a habit yet.

> **The rule: add a plugin only after the habit hurts without it.**

### Stage 1 — make the habit possible (install now)

| Plugin | Why |
|---|---|
| **Templater** | Templates with real dates and prompts. Everything in §4 needs it. |
| **Periodic Notes** | Weekly notes for reports and reflection, on a schedule. |
| **Omnisearch** *(optional)* | Better search ranking. But try built-in search first — see §5.1, it is free and Omnisearch holds an index in memory. |
| **Folder Notes** | Makes the `_index.md` pattern work — click a folder, get its landing page. |
| *(already installed)* **Homepage Studio** | Home dashboard, writing heatmap, journal, tasks. |

Obsidian **Bases** is now built in — use it before installing Dataview. xupisco's
10 `.base` files are the best examples of what it can do; start by reading
`Assorted/Bases/Tasks - Reloaded.base`.

### Stage 2 — navigation, once the vault is big enough to get lost in

Cycle Through Panes · Float Search · Dashboard Navigator · File Explorer Note Count

### Stage 3 — polish, when things annoy you

Style Settings · Iconic · Code Styler · Linter · Advanced URI

### Stage 4 — only when Claude Code arrives

Everything in `.claude/`, MCP servers, and the pull scripts from lukeinglis.

**Adopt xupisco's CSS habit from day one**: one snippet per plugin,
`plugin_<name>.css`. When something looks broken, you toggle one file off and know
immediately which plugin caused it.

### 5.1 Memory budget — 16 GB machine

Obsidian is an Electron app. A base vault costs roughly 300–500 MB. Plugins are what
push it past a gigabyte, and a few specific ones are far worse than the rest.

**Never install these on this machine:**

| Plugin | Why it is expensive |
|---|---|
| **Smart Connections** | Runs a local embedding model and keeps vectors in memory. This is what produces xupisco's `.smart-env/` folder — 100+ `.ajson` files for a vault with about 20 real notes. On 16 GB, with a browser and an editor open, this is the one that will hurt. |
| **Copilot / Smart Composer / Text Generator** | Same class: local models or large in-memory caches. |
| **Omnisearch** *(with caution)* | Builds a full-text index of the whole vault in memory. Fine at a few hundred notes; watch it past a few thousand. Obsidian's built-in search costs nothing — start there and only add Omnisearch when built-in search actually fails you. |
| **Excalidraw** | Heavy editor, loads on startup. Install only if you really draw. |

**Cheap and worth it:** Templater, Periodic Notes, Folder Notes, Style Settings,
Iconic, Linter. These are small and mostly idle.

**Rules for a 16 GB machine**
- Stay under **10 community plugins**. xupisco's 49 is a showcase, not a target.
- Prefer built-in **Bases** over Dataview. Dataview re-indexes the vault and keeps a
  live query engine running; Bases is native and lighter.
- Keep the vault under a few thousand notes. Archive aggressively into `99-Archive/`.
- Do not put large binaries in the vault (xupisco commits a `.tar.gz` vector DB —
  do not imitate that). PDFs and images belong in an `attachments/` folder you can
  exclude from search.
- Check the real cost yourself: `Ctrl+Shift+I` → Memory tab, or Task Manager.
  Do it once with plugins off and once with them on, so you know what each one costs.

---

## 6. How to actually study the two repos

Reading a repo on GitHub teaches you much less than opening it as a vault.

### Exercise 1 — open xupisco as a real vault (30 min)

```bash
git clone https://github.com/xupisco/obsidian-sample-vault
```

Open the folder in Obsidian, trust the plugins. Then:
- Open **Settings → Appearance → CSS snippets**. Toggle `plugin_dataview.css` off
  and on. Watch what changes. That is the per-plugin snippet pattern doing its job.
- Open `Assorted/Bases/Vault monitor.base`. This is a dashboard over your own vault.
- Open `Assorted/Dataview Cheat Sheet.md` — it is a genuinely good reference, keep it.
- Look at `.obsidian/hotkeys.json`. Steal the bindings that match how you already
  move in Neovim.

**Do this in a throwaway vault, not your work vault.**

### Exercise 2 — read lukeinglis as a system (45 min)

Read in this order:
1. `docs/philosophy.md` — the reasoning
2. `Templates/meeting.md` — see the HTML-comment instruction pattern
3. `docs/examples/decision-record.md` — see a filled-in result
4. `.claude/rules/meeting-workflow.md` — see how the rules encode the workflow
5. `README.md` last — it is a feature list, least useful for learning

While reading, write down for each template: **what would I put in this, this week?**
If the answer is "nothing", you do not need that template.

### Exercise 3 — one week of manual operation (7 days)

Before automating anything, run the system by hand:
- every meeting gets a file in `03-Meetings/`
- everything you are unsure about goes to `04-Inbox/`
- write both reports
- write one reflection

At the end of the week you will know which parts you actually use. **Delete the rest.**
A vault with 4 templates you use beats one with 13 you do not.

---

## 7. Making it yours

Where your vault should deliberately differ from both references:

| Their choice | Your choice | Why |
|---|---|---|
| `01-Components/` (product domains) | `01-Projects/` (repos and workstreams) | You are an engineer, not a PM. A repo is your permanent domain. |
| Weekly cadence | **Twice weekly** | Matches your reporting rhythm. The report is the forcing function. |
| No reflection layer | `07-Reflection/` | You asked for it, and neither vault has it. |
| Decisions inside components | Same, but seeded from **commit messages** | Your decisions already exist in git history. Mine them, do not retype them. |
| AI does the triage | **You do it by hand, for now** | Builds the routing intuition that makes automation trustworthy later. |
| Vault is a git repo | **Vault is never a git repo** | Company constraint, see §2.1. |

**The one thing you should not change**: one meeting per file, one decision per file.
Every automation, every search, every future AI assist depends on it.

---

## 8. Phases

| # | Phase | Time | Output |
|---|---|---|---|
| 0 | Exercise 1 + 2 — study both repos in a throwaway vault | 1.5 h | Notes on what you want |
| 1 | Create the folder skeleton (§3) + Stage 1 plugins (§5) | 1 h | Empty but correct vault |
| 2 | Write 4 templates: meeting, decision, report, reflection | 1 h | `Templates/` |
| 3 | Exercise 3 — one week of manual operation | 7 days | Evidence of what you use |
| 4 | Add the git bridge to the global justfile (§4.1) | 30 min | `just -g report-commits` |
| 5 | Prune. Delete unused templates and folders. | 30 min | A vault you trust |
| 6 | Set up the config↔repo sync script (§2.1) | 30 min | `obsidian-vault` branch is real |
| 7 | Stage 2 plugins, only where you felt friction | as needed | |
| 8 | **When Claude Code arrives**: port lukeinglis's commands | later | `/report`, `/decision`, `/triage` |

Do 0–3 first. Everything after that is a response to a problem you actually hit.

---

## 9. Open questions

1. **Where does the real vault live on the company laptop?** It must be a path that
   backs up (OneDrive is fine for backup, but check company policy before syncing).
2. **Do you already use a note tool at work?** If there is an existing place where
   meeting notes go, this vault has to either replace it or clearly sit beside it.
   Two systems means neither gets used.
3. **Who reads the twice-weekly report?** If it goes to a manager in Slack or email,
   the template's top three bullets should be written for them, not for you.
4. **Recurring meetings** — list them. Each one gets a folder in `03-Meetings/`, and
   that list is the fastest way to make the vault feel useful on day one.
