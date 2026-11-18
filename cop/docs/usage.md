# Using cop

## Install

```bash
pip install --user playwright
ln -s "$PWD/cop/cop" ~/bin/cop
```

`playwright install` is not needed: cop attaches to the Edge you already have.
Optional renderers, used in this order: `glow`, `bat`, Python `rich`
(`pip install --user rich`), then the built-in `md.awk`, which needs nothing
beyond Git Bash. Piped or redirected output stays plain markdown.

## First run

```bash
cop up
```

Opens Edge with its own profile in `~/.cop/edge` and the DevTools port on 9222.
Sign in once in that window. Keep the window open (minimised is fine); the login
survives restarts because the profile lives on disk.

## Commands

| Command | What |
|---|---|
| `cop` | chat loop in the current session (`:e` editor, `:u` switch, `:n NAME` new, `:q` quit) |
| `cop ask [TEXT]` / `cop TEXT...` | one prompt; with no TEXT, opens `$EDITOR` |
| `cmd \| cop ask "why?"` | piped input is appended as a code block |
| `cop new [NAME]` | start a session and switch to it |
| `cop use [NAME]` | switch session, fzf when NAME is omitted |
| `cop list` | fzf picker, enter switches |
| `cop close [NAME]` | leave the current session |
| `cop delete [NAME...]` | forget sessions; no NAME opens fzf multi-select, `all` clears everything |
| `cop last` | show the last reply again, no browser call |
| `cop probe` | write the page's accessibility tree to `~/.cop/probe.txt` |

## How it works

- A session is a name mapped to a Copilot conversation URL in
  `~/.cop/sessions.tsv`. The URL is recorded after the first reply, so `use`
  reopens the same conversation in the single Copilot tab.
- `delete` only forgets the local name; the conversation stays in Copilot's
  history.
- The reply is taken from Copilot's own **Copy** button, which yields clean
  markdown with code blocks. This overwrites the system clipboard.
- Completion is detected when the Stop button disappears and a new Copy button
  appears.

## Settings

| Variable | Default |
|---|---|
| `COP_HOME` | `~/.cop` |
| `COP_PORT` | `9222` |
| `COP_EDGE` | auto-detected `msedge.exe` |
| `COP_PYTHON` | first of `python`, `python3`, `py` |
| `COP_TIMEOUT` | `600` seconds per reply |
| `COP_RENDER` | `glow`, else `bat`, else `rich`, else `md.awk` |

`127.0.0.1` is added to `NO_PROXY` so a corporate proxy does not swallow the
DevTools connection.

## When Copilot changes its page

Run `cop probe`, look up the role and name of the input box, Stop button and
Copy button in `~/.cop/probe.txt`, then override them in
`~/.cop/selectors.json`:

```json
{
  "input": "role=textbox[name=/message copilot/i]",
  "stop": "role=button[name=/stop/i]",
  "copy": "role=button[name=/^copy$/i]",
  "reply": "[role=article]"
}
```

Each value is a Playwright selector or a list of them; the first that matches wins.
