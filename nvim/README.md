# nvim — Windows branch

LazyVim plus a **workbench layer** that reproduces herdr's key semantics inside
Neovim, because herdr does not run on this machine.

```
Linux                              Windows (this branch)
  C-a  ->  herdr                     C-a  ->  Neovim workbench layer
           tab / pane / agent                 tabpage / window / terminal buffer
```

Same keys, same meaning, different owner. See
[`plans/cross-platform-workbench.md`](../plans/cross-platform-workbench.md) for the
full design.

## Install

Requires **Neovim 0.12.4+**, Git for Windows, ripgrep, fd, and a C compiler for
treesitter (`zig` is the least painful).

```powershell
winget install Neovim.Neovim Git.Git BurntSushi.ripgrep.MSVC sharkdp.fd zig.zig
```

Link this directory to where Neovim looks for its config. Run in Git Bash:

```bash
REPO=$(cygpath -w "$PWD")
cmd //c mklink //J "%LOCALAPPDATA%\nvim" "$REPO"
```

First launch installs plugins. Try it in a sandbox first, which touches nothing:

```bash
NVIM_APPNAME=lazyvim nvim
```

## Keys

Everything below is prefixed with `C-a`, and every binding works in **normal mode
and terminal mode**, so it still responds while an agent is running in a pane.

| Key | Action | herdr equivalent |
|---|---|---|
| `C-a \|` / `C-a -` | split vertical / horizontal | `split_vertical` / `split_horizontal` |
| `C-a h/j/k/l` | move focus | `focus_pane_*` |
| `C-a c` | new tab | `new_tab` |
| `C-a r` | **rename tab** | `rename_tab` |
| `C-a q` | close tab | `close_tab` |
| `C-a C-h` / `C-a C-l` | previous / next tab | `previous_tab` / `next_tab` |
| `C-a 1..9` | jump to tab by number | `switch_tab` |
| `C-a w` | close pane | `close_pane` |
| `C-a z` | toggle zoom | `zoom` |
| `C-a J` / `C-a K` | resize pane | `resize_mode` |
| `C-a s` | workspace picker | `workspace_picker` |
| `C-a C-p` | command palette | `jt.command-palette.open` |
| `C-a C-f` | file viewer | herdr-file-viewer |
| `C-a a` | open an agent pane | — |
| `C-a d` | save session now | `detach` (closest equivalent) |
| `C-a [` | leave terminal insert mode | `copy_mode` |
| `C-a C-a` | send a literal `C-a` (increment number) | tmux `send-prefix` |

Editor keys stay on bare Ctrl and `<Space>`, so the three layers never collide:
`C-p` files, `C-f` grep, `C-b` buffers, `C-n` file tree, `C-s` substitute.

### Mouse

Tabs are clickable. Single click switches, **double click renames**, middle click
closes.

## Session restore

Windows restarts without warning, so save-on-exit is not enough: a forced reboot
never runs `VimLeavePre`. This config saves in three ways instead.

| Trigger | When |
|---|---|
| Timer | every 60 seconds |
| Layout change | 2 s after `TabNew`, `TabClosed` or `BufWritePost` |
| Clean exit | `VimLeavePre`, as a cheap extra |

A bare `nvim` restores the session for the current directory automatically.
Opening a specific file (`nvim foo.lua`) does not, because that is clearly not what
you asked for.

Tab names need their own handling: `:mksession` does not persist tab-scoped
variables, so `vim.t.tabname` is written to a sidecar JSON file beside the session
and re-applied after the session loads.

```
%LOCALAPPDATA%\nvim-data\sessions\
  %C%Users%you%code%myproject.vim     <- :mksession output
  %C%Users%you%code%myproject.json    <- tab names
```

Commands: `:SessionSave`, `:SessionRestore`, `:SessionClear`.

**Verified** on Neovim 0.12.4 by killing the process with `SIGKILL` (exit 137, no
clean shutdown at all) and restarting: two tabs, a split inside the second tab, and
both custom tab names all came back.

Terminal buffers are deliberately excluded from `sessionoptions`. Restoring a dead
shell is worse than not restoring it.

## Memory

This config targets a **16 GB** machine.

- `lua/plugins/lean.lua` keeps the treesitter parser list short, leaves
  `mason.ensure_installed` empty, and enables the big-file guard.
- Language servers are the real cost, not Neovim. Install them one at a time with
  `:Mason` and keep the number of running servers small.
- Background update checking is off. Run `:Lazy update` by hand.

## Layout

```
init.lua                    entry point
lua/config/
  lazy.lua                  lazy.nvim + LazyVim bootstrap
  options.lua               option overrides, plus the Git Bash shell on Windows
  keymaps.lua               bare-Ctrl and leader layers
  autocmds.lua
lua/plugins/
  workbench.lua             wires the workbench layer into the lazy lifecycle
  ui.lua                    disables bufferline so the tab row is free
  lean.lua                  memory budget
lua/workbench/
  init.lua                  the C-a prefix layer
  tabline.lua               named, clickable tabs
  session.lua               crash-safe session persistence
```

The workbench layer is off by default on Linux, because there the real herdr owns
`C-a`. Force it on with `vim.g.workbench = true` if you want to try it.
