BEGIN {
  E = "\033["; R = E "0m"; B = E "1m"; D = E "2m"; I = E "3m"; U = E "4m"
  H1 = E "1;35m"; H2 = E "1;33m"; H3 = E "1;36m"; C = E "36m"; K = E "32m"
  code = 0
}

# >>> apply inline markdown: bold, italic, code, links <<< #
function inl(s) {
  while (match(s, /\[[^]]+\]\([^)]+\)/)) {
    t = substr(s, RSTART, RLENGTH); p = index(t, "](")
    s = substr(s, 1, RSTART - 1) U substr(t, 2, p - 2) R D " (" substr(t, p + 2, length(t) - p - 2) ")" R substr(s, RSTART + RLENGTH)
  }
  while (match(s, /`[^`]+`/))
    s = substr(s, 1, RSTART - 1) C substr(s, RSTART + 1, RLENGTH - 2) R substr(s, RSTART + RLENGTH)
  while (match(s, /\*\*[^*]+\*\*/))
    s = substr(s, 1, RSTART - 1) B substr(s, RSTART + 2, RLENGTH - 4) R substr(s, RSTART + RLENGTH)
  while (match(s, /\*[^* ][^*]*\*/))
    s = substr(s, 1, RSTART - 1) I substr(s, RSTART + 1, RLENGTH - 2) R substr(s, RSTART + RLENGTH)
  return s
}

/^[ \t]*```/ {
  code = !code
  lang = $0; sub(/^[ \t]*```/, "", lang)
  print D (code ? "┌─ " lang : "└─") R
  next
}
code { print D "│ " R K $0 R; next }
/^# /    { sub(/^# /, "");    print H1 inl($0) R; next }
/^## /   { sub(/^## /, "");   print H2 inl($0) R; next }
/^#+ /   { sub(/^#+ /, "");   print H3 inl($0) R; next }
/^[ \t]*[-*_][ \t]*[-*_][ \t]*[-*_][-*_ \t]*$/ { print D "────────────────────────────────" R; next }
/^> ?/   { sub(/^> ?/, "");   print D "▎ " I inl($0) R; next }
/^[ \t]*[-*+] / {
  match($0, /^[ \t]*/); pad = substr($0, 1, RLENGTH)
  sub(/^[ \t]*[-*+] /, ""); print pad "  • " inl($0); next
}
{ print inl($0) }
