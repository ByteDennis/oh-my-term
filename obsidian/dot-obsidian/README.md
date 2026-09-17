# dot-obsidian

Obsidian settings, mirrored out of the real vault.

Most of this directory starts empty on purpose. Obsidian writes its own settings
files, and hand-written guesses at their schema go stale. Configure things in the
app, then run `scripts/push-config.sh` to copy them here.

`community-plugins.json` is checked in as a starting list. Everything else appears
after the first push.

Never committed: `workspace.json` (records which files you had open),
`plugins/*/data.json` (often contains note text), and plugin bundles.
