# nvim — Windows branch

LazyVim plus a **workbench layer** that reproduces herdr's key semantics inside
Neovim, because herdr does not run on this machine.

```
Linux                              Windows (this branch)
  C-a  ->  herdr                     C-a  ->  Neovim workbench layer
           tab / pane / agent                 tabpage / window / terminal buffer
```

Same keys, same meaning, different owner.

```
init.lua            entry point
lua/config/         LazyVim bootstrap, options, keymaps
lua/plugins/        plugin specs, including the memory budget
lua/workbench/      the C-a layer: prefix keys, tabline, session persistence
docs/               keys, sessions, proxy
```

Requires Neovim 0.12.4+, Git for Windows, ripgrep, fd, and a C compiler.

- [`docs/keys.md`](docs/keys.md) — the full key map
- [`docs/sessions.md`](docs/sessions.md) — how state survives a forced restart
- [`docs/proxy.md`](docs/proxy.md) — installing plugins behind a proxy
- [`plans/cross-platform-workbench.md`](../plans/cross-platform-workbench.md) — the design, on `main`
