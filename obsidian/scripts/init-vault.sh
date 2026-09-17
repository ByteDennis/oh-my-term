#!/usr/bin/env bash
# Create the folder skeleton in a real vault and copy templates in.
# Safe to re-run: it never overwrites an existing file.
set -euo pipefail

VAULT="${1:-}"
if [ -z "$VAULT" ]; then
  echo "usage: $0 /path/to/vault" >&2
  exit 1
fi

HERE="$(cd "$(dirname "$0")/.." && pwd)"

# >>> create the folder skeleton <<< #
mkdir -p "$VAULT"/{01-Projects,02-Reports/_drafts,03-Meetings/_one-off,04-Inbox,05-People,06-Clippings,07-Reflection,99-Archive,Templates,attachments}

# >>> copy templates without clobbering edited ones <<< #
for f in "$HERE"/templates/*.md; do
  dest="$VAULT/Templates/$(basename "$f")"
  if [ -e "$dest" ]; then
    echo "skip   $dest (already exists)"
  else
    cp "$f" "$dest"
    echo "create $dest"
  fi
done

# >>> seed the home note <<< #
if [ ! -e "$VAULT/00-Home.md" ]; then
  cat > "$VAULT/00-Home.md" <<'HOME'
---
title: Home
tags: [home]
---

# Home

## This week

## Open projects

## Inbox
HOME
  echo "create $VAULT/00-Home.md"
fi

# >>> the vault must never become a git repo <<< #
if [ -d "$VAULT/.git" ]; then
  echo
  echo "WARNING: $VAULT contains a .git directory." >&2
  echo "The vault holds company content and must never be a git repo." >&2
fi

echo
echo "done. Open $VAULT in Obsidian."
