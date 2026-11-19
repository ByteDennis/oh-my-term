"""Interactive terminal front end; the bash launcher owns sessions and sending."""
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.key_binding import KeyBindings
except ImportError:
    sys.exit("cop: interactive mode needs prompt_toolkit; install with: python -m pip install prompt_toolkit")

HOME = Path(os.environ.get("COP_HOME", Path.home() / ".cop"))
SCRIPT = Path(__file__).with_name("cop").as_posix()
COMMANDS = [":help", ":new", ":use", ":sessions", ":status", ":doctor", ":last", ":editor",
            ":file", ":export", ":stream", ":quit"]


def current():
    path = HOME / "current"
    return path.read_text(encoding="utf-8").strip() if path.exists() else "(new chat)"


def run(*args, prompt=None):
    env = dict(os.environ, COP_STATUS="1")
    kwargs = {"input": prompt} if prompt is not None else {}
    return subprocess.run(["bash", SCRIPT, *args], text=True, env=env, **kwargs).returncode


def transcript():
    name = hashlib.sha256(current().encode()).hexdigest()
    return HOME / "transcripts" / (name + ".jsonl")


def record(prompt):
    path = transcript()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output:
        output.write(json.dumps({"prompt": prompt, "reply": (HOME / "last.md").read_text(encoding="utf-8")}) + "\n")


def export(path):
    source = transcript()
    if not source.exists():
        print("No recorded turns in this session yet.")
        return
    turns = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
    content = "# " + current() + "\n\n" + "\n\n".join(
        f"## You\n\n{turn['prompt']}\n\n## Copilot\n\n{turn['reply']}" for turn in turns)
    # Exclusive creation keeps an export from overwriting an existing file.
    with Path(path).expanduser().open("x", encoding="utf-8") as output:
        output.write(content + "\n")
    print(f"Exported {len(turns)} turns to {path}")


def main():
    HOME.mkdir(parents=True, exist_ok=True)
    keys = KeyBindings()

    @keys.add("enter")
    def submit(event):
        event.current_buffer.validate_and_handle()

    @keys.add("escape", "enter")
    def newline(event):
        event.current_buffer.insert_text("\n")

    session = PromptSession(
        history=FileHistory(str(HOME / "history")),
        completer=WordCompleter(COMMANDS), complete_while_typing=False,
        multiline=True, key_bindings=keys,
        prompt_continuation=lambda width, line, soft: "...: ".rjust(width),
        bottom_toolbar=lambda: f" {current()} | Enter send | Alt+Enter newline | Ctrl+C cancel | Ctrl+D exit ",
    )
    print("cop — interactive Copilot\n:help commands · Up/Down history · Ctrl+R search history")
    run("status")
    number, files = 1, []
    while True:
        try:
            text = session.prompt(f"In [{number}]: ").strip()
            if not text:
                continue
            if text.startswith(":"):
                command, _, argument = text.partition(" ")
                argument = argument.strip()
                if command in (":q", ":quit"):
                    break
                if command == ":help":
                    print(":new [NAME] · :use [NAME] · :sessions [SEARCH] · :status · :doctor · :last\n"
                          ":editor · :file PATH (attach to next prompt) · :export PATH\n"
                          ":stream on|off · :quit\nEnter sends; Alt+Enter adds a line. Ctrl+C clears/cancels; Ctrl+D exits.")
                elif command == ":file":
                    parts = shlex.split(argument, posix=False)
                    path = Path(" ".join(parts).strip('\"\'')).expanduser()
                    content = path.read_text(encoding="utf-8")
                    files.append((path.name, content))
                    print(f"Attached {path.name} to the next prompt.")
                elif command == ":export":
                    if not argument:
                        print("Usage: :export PATH")
                    else:
                        export(argument.strip('\"\''))
                elif command == ":stream":
                    if argument not in ("on", "off"):
                        print("Usage: :stream on|off")
                    else:
                        os.environ["COP_STREAM"] = "1" if argument == "on" else "0"
                        print(f"Streaming {argument}.")
                elif command in (":sessions", ":list"):
                    # List and search without opening fzf or the browser.
                    db = HOME / "sessions.tsv"
                    for line in db.read_text(encoding="utf-8").splitlines() if db.exists() else []:
                        name = line.split("\t")[0]
                        if argument.casefold() in name.casefold():
                            print(("* " if name == current() else "  ") + name)
                elif command in (":n", ":new", ":u", ":use", ":status", ":doctor", ":last", ":e", ":editor"):
                    cmd = {":n": "new", ":new": "new", ":u": "use", ":use": "use",
                           ":e": "ask", ":editor": "ask"}.get(command, command[1:])
                    run(cmd, *([argument] if argument else []))
                else:
                    print("Unknown command; use :help.")
                continue
            prompt = text
            for name, content in files:
                fence = "```"
                while fence in content:
                    fence += "`"
                prompt += f"\n\nFile: {name}\n{fence}\n{content}\n{fence}"
            print(f"Out[{number}]:", flush=True)
            if run("ask", prompt=prompt) == 0:
                record(prompt)
                files.clear()
                number += 1
        except KeyboardInterrupt:
            print("\nCancelled. You can enter another prompt.")
        except EOFError:
            break
        except (OSError, ValueError) as exc:
            print(f"cop: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
