# Language servers, and whether you need Mason

## What Mason actually does

Mason is a downloader, nothing more. It fetches prebuilt binaries into
`mason/packages/`, puts shims in `mason/bin/`, and prepends that directory to
Neovim's `PATH`. At runtime it does nothing at all.

For reference, a small install on a Linux machine:

```
23M  lua-language-server
13M  stylua
2.8M shfmt
```

That is the whole value proposition: you do not have to install those yourself.

## You do not need it

Any language server on `PATH` works without Mason. `nvim-lspconfig` looks up the
executable by name, and Neovim 0.12's `vim.lsp.config` / `vim.lsp.enable` only
need a command.

Reasons to skip it on a locked-down Windows machine:

- One fewer downloader to get through the proxy.
- Corporate machines usually already have Node and Python, which ship most of the
  servers you would want anyway.
- Endpoint protection tends to dislike freshly downloaded unsigned executables
  appearing in `%LOCALAPPDATA%`. Installing through a package manager the company
  already allows avoids that argument entirely.

Installing servers yourself:

```bash
npm  install -g typescript-language-server typescript vscode-langservers-extracted
pip  install  'python-lsp-server[all]'   # or: pip install pyright
winget install LLVM.LLVM                 # clangd
```

## What this config does

`lua/plugins/lean.lua` leaves `mason.ensure_installed` empty. Mason is present but
installs nothing on its own, so:

- servers you install yourself are found on `PATH`
- `:Mason` is still there when you want one that is awkward to install by hand
- nothing downloads behind your back on first launch

This is the low-risk middle ground and it is the recommended setting.

## Removing Mason entirely

```lua
-- lua/plugins/lean.lua
{ "williamboman/mason.nvim", enabled = false },
{ "williamboman/mason-lspconfig.nvim", enabled = false },
```

LazyVim wires Mason into its LSP setup, so verify this rather than assuming it
works: disable them, start Neovim, run `:checkhealth lsp`, and open a file in a
language you have a server for. If LazyVim errors on a missing Mason, keep the
middle ground above instead.

## Keep the count small

Each running server is a separate process, and a few of them are not small:
`typescript-language-server` and `rust-analyzer` routinely sit in the hundreds of
megabytes, `rust-analyzer` well past a gigabyte on a large workspace. On a 16 GB
machine the number of servers running at once matters far more than anything
Neovim itself does.

Enable servers for the languages you use this month, not the ones you might use.
