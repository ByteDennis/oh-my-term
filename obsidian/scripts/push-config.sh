#!/usr/bin/env bash
# Copy config and templates FROM the real vault INTO this repo.
#
# Content never moves. Only settings, snippets and templates do, and the excludes
# below are the part that matters: workspace.json records the paths of files you
# had open, and plugin data.json files can contain note text.
set -euo pipefail

VAULT="${1:-}"
if [ -z "$VAULT" ]; then
  echo "usage: $0 /path/to/vault" >&2
  exit 1
fi

HERE="$(cd "$(dirname "$0")/.." && pwd)"

rsync -a --delete \
  --exclude 'README.md' \
  --exclude 'workspace.json' \
  --exclude 'workspace-mobile.json' \
  --exclude 'plugins/*/data.json' \
  --exclude 'plugins/*/main.js' \
  --exclude 'plugins/*/styles.css' \
  --exclude 'themes/' \
  "$VAULT/.obsidian/" "$HERE/dot-obsidian/"

rsync -a "$VAULT/Templates/" "$HERE/templates/"

echo "pulled config into $HERE"
echo
echo "Now review the diff before committing. You are looking for project names,"
echo "people's names, and file paths that should not leave the machine:"
echo
echo "    git -C $HERE diff"
