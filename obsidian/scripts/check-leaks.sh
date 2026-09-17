#!/usr/bin/env bash
# Rough check for content that should not be committed.
# Not a security tool. It catches the obvious mistakes, not a determined one.
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
fail=0

# >>> files that record what you had open <<< #
for bad in workspace.json workspace-mobile.json; do
  if find "$HERE" -name "$bad" | grep -q .; then
    echo "LEAK: $bad is present; it records open file paths" >&2
    fail=1
  fi
done

# >>> plugin state often embeds note content <<< #
if find "$HERE/dot-obsidian" -name data.json 2>/dev/null | grep -q .; then
  echo "WARN: plugin data.json found; check it for note content" >&2
fi

# >>> templates must stay generic <<< #
if grep -rIl --exclude-dir=.git -E '^[^<]*\b(19|20)[0-9]{2}-[0-9]{2}-[0-9]{2}\b' "$HERE/templates" 2>/dev/null | grep -q .; then
  echo "WARN: a hard-coded date in templates/ suggests a real note got copied in" >&2
fi

[ "$fail" -eq 0 ] && echo "no obvious leaks"
exit "$fail"
