# Session restore

Windows restarts without warning, and a forced restart never runs `VimLeavePre`.
Any save-on-exit scheme therefore loses whatever happened since the last clean
quit. This config saves three ways instead.

| Trigger | When |
|---|---|
| Timer | every 60 seconds |
| Layout change | 2 s after `TabNew`, `TabClosed` or `BufWritePost` |
| Clean exit | `VimLeavePre`, as cheap insurance |

A bare `nvim` restores the session for the current directory. Opening a specific
file (`nvim foo.lua`) does not, because that is clearly not what you asked for.

## Tab names

`:mksession` does not persist tab-scoped variables, so `vim.t.tabname` would be
lost. It is written to a sidecar JSON file beside the session and re-applied after
the session is sourced.

```
%LOCALAPPDATA%\nvim-data\sessions\
  %C%Users%you%code%myproject.vim     :mksession output
  %C%Users%you%code%myproject.json    tab names
```

## Commands

`:SessionSave` · `:SessionRestore` · `:SessionClear`

## Verified

On Neovim 0.12.4, by killing the process with `SIGKILL` (exit 137, no shutdown
path at all) and restarting: two tabs, a split inside the second tab, and both
custom tab names all came back.

Terminal buffers are deliberately excluded from `sessionoptions`. Restoring a dead
shell is worse than not restoring it.
