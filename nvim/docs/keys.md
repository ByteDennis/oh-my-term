# Keys

Three layers that must never overlap:

| Layer | Trigger | Owner |
|---|---|---|
| Workbench | `C-a` + key | `lua/workbench/` — herdr semantics |
| Navigation | bare `Ctrl` | editor |
| Features | `<Space>` | editor |

On Linux the real herdr takes `C-a` before Neovim sees it, so the workbench layer
is disabled there by default. Force it on with `vim.g.workbench = true`.

## Workbench layer

Every binding works in **normal mode and terminal mode**, so it still responds
while an agent is running in a pane.

| Key | Action | herdr equivalent |
|---|---|---|
| `C-a \|` / `C-a -` | split vertical / horizontal | `split_vertical` / `split_horizontal` |
| `C-a h/j/k/l` | move focus | `focus_pane_*` |
| `C-a c` | new tab | `new_tab` |
| `C-a r` | rename tab | `rename_tab` |
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
| `C-a d` | save session now | `detach`, as close as this gets |
| `C-a [` | leave terminal insert mode | `copy_mode` |
| `C-a C-a` | send a literal `C-a` (increment number) | tmux `send-prefix` |

## Editor layers

`C-p` files · `C-f` grep · `C-b` buffers · `C-n` file tree · `C-s` substitute

`<leader>t` terminal · `<leader>rn` rename · `<leader>.` code action ·
`<leader>f` format

## Mouse

Tabs are clickable: single click switches, **double click renames**, middle click
closes.
