# Using cop

## Install

In Git Bash:

```bash
git clone -b copilot https://github.com/ByteDennis/oh-my-term.git ~/oh-my-term
python -m pip install --user playwright prompt_toolkit
echo 'export PATH="$HOME/oh-my-term/cop:$PATH"' >> ~/.bashrc
source ~/.bashrc
cop up
```

Behind a proxy, export `HTTPS_PROXY` before `pip install`. Put the directory on
`PATH` rather than linking the script: Git Bash's `ln -s` copies by default, and a
copied `cop` can no longer find `cop.py`. Check `python --version` first; if it
opens the Microsoft Store, set `COP_PYTHON=py`.

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
| `cop` | IPython-style prompt, numbered turns, persistent history, multiline editing (`:help` for commands) |
| `cop ask [TEXT]` / `cop TEXT...` | one prompt; with no TEXT, opens `$EDITOR` |
| `cmd \| cop ask "why?"` | piped input is appended as a code block |
| `cop new [NAME]` | start a session and switch to it |
| `cop use [NAME]` | switch session, fzf when NAME is omitted |
| `cop list` | fzf picker, enter switches |
| `cop close [NAME]` | leave the current session |
| `cop delete [NAME...]` | forget sessions; no NAME opens fzf multi-select, `all` clears everything |
| `cop last` | show the last reply again, no browser call |
| `cop probe` | write the page's accessibility tree to `~/.cop/probe.txt` |
| `cop status` | inspect connection/login without opening a window or navigating |

## Interactive editing

`Enter` sends, `Alt+Enter` inserts a newline, Up/Down recalls history, Ctrl+R
searches history, Ctrl+C clears/cancels, and Ctrl+D exits. Bracketed paste keeps
multiline text together. `Out[n]` identifies each response; status messages
report connection, login requirements, waiting and completion on stderr.

| Prompt command | Behavior |
|---|---|
| `:new [NAME]` / `:n [NAME]` | New conversation |
| `:use [NAME]` / `:u [NAME]` | Resume a session (fzf picker when omitted) |
| `:sessions [SEARCH]` | List/search saved session names |
| `:status` | Connection and sign-in status |
| `:editor` / `:e` | Compose with `$EDITOR` |
| `:last` | Render the saved reply again |
| `:file PATH` | Attach a UTF-8 text/code file to the next prompt |
| `:export PATH` | Export recorded interactive turns from the current session as Markdown; refuses overwrite |
| `:stream on` / `:stream off` | Optional live plain-text response display; default off |
| `:quit` / `:q` | Exit |

History and successful prompt/response pairs are saved locally in `~/.cop`.
Exports cover recorded interactive turns, not the browser's entire chat history
or one-shot/editor turns. Streaming uses visible message text; normal mode uses
the final Copy result for Markdown. Ctrl+C attempts to stop browser generation
and releases the prompt lock. Failed requests preserve the last successful reply.

## How it works

- A session is a name mapped to a Copilot conversation URL in
  `~/.cop/sessions.tsv`. The URL is recorded after the first reply, so `use`
  reopens the same conversation in the single Copilot tab.
- `delete` only forgets the local name; the conversation stays in Copilot's
  history.
- The reply is taken from Copilot's own **Copy** button, which yields clean
  markdown with code blocks. This overwrites the system clipboard.
- New message text is compared with the pre-send snapshot, excluding an exact
  prompt echo. Completion waits for Stop to disappear and text/buttons to settle.
  Text extraction also works without Copy/Stop controls. Without a Stop indicator,
  completion uses an inactivity interval; increase `COP_SETTLE` for slow streams.
- Conversation URLs retain their query parameters. An unsaved active conversation
  is reused rather than reloaded on every send. Authentication tabs are preserved
  while you sign in, and normal requests do not bring the window to the foreground.
- Browser sessions can still expire under Microsoft/company policy; persistence
  cannot bypass that. The driver reports sign-in requirements and waits in the
  existing window for up to `COP_LOGIN_TIMEOUT` seconds.

## Settings

| Variable | Default |
|---|---|
| `COP_HOME` | `~/.cop` |
| `COP_PORT` | `9222` |
| `COP_EDGE` | auto-detected `msedge.exe` |
| `COP_PYTHON` | first of `python`, `python3`, `py` |
| `COP_TIMEOUT` | `600` seconds per reply |
| `COP_LOGIN_TIMEOUT` | `120` seconds waiting for chat input/sign-in |
| `COP_SETTLE` | `3` seconds without response changes before completion |
| `COP_STATUS` | `1` in interactive mode/terminal stderr, otherwise off |
| `COP_STREAM` | `0`; use `1` for live plain text on stderr |
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
  "assistant": "[data-message-author-role=assistant]",
  "reply": "[role=article]"
}
```

Each value is a Playwright selector or a list of them; the first that matches wins.
For response snapshots, assistant-specific selectors take priority, then generic
reply selectors are checked. Actual Microsoft selectors need verification in your
signed-in browser; local mock-page tests do not establish Microsoft compatibility.
