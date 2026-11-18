# cop

Microsoft 365 Copilot chat from Git Bash. One persistent Edge window holds the
login; `cop` drives it over the DevTools port and prints each reply as markdown.

| File | What |
|---|---|
| `cop` | bash front end: sessions, fzf picker, chat loop |
| `cop.py` | Playwright driver that talks to the Edge window |
| `md.awk` | zero-dependency markdown colouring for the terminal |

Setup, commands and troubleshooting: [docs/usage.md](docs/usage.md).
