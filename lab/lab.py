"""Readable Git and GitLab workflows. No shell evaluation or credential storage."""
import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


def parser():
    ap = argparse.ArgumentParser(prog="lab", description="Interactive Git and GitLab workbench; run without a command for a prompt.")
    ap.add_argument("-C", "--directory", help="work in this repository/worktree")
    ap.add_argument("--repo", help="GitLab repository URL override (otherwise glab uses your Git remote)")
    ap.add_argument("--dry-run", action="store_true", help="print the underlying command without executing it")
    sub = ap.add_subparsers(dest="command")
    sub.add_parser("status", help="branch, staged/unstaged files, and upstream divergence")
    diff = sub.add_parser("changes", help="show changes")
    diff.add_argument("--staged", action="store_true")
    diff.add_argument("paths", nargs="*")
    stage = sub.add_parser("stage", help="stage named paths, or explicitly --all")
    stage.add_argument("paths", nargs="*")
    stage.add_argument("--all", action="store_true")
    unstage = sub.add_parser("unstage", help="remove named paths from staging, keeping files")
    unstage.add_argument("paths", nargs="+")
    commit = sub.add_parser("commit", help="commit staged changes")
    commit.add_argument("-m", "--message", help="commit message; omit to open Git's editor")
    amend = sub.add_parser("amend", help="amend HEAD with staged changes; never pushes")
    amend.add_argument("-m", "--message", help="replacement message; omitted means keep the message")
    sub.add_parser("log", help="show recent commits")
    sub.add_parser("branches", help="list local branches and upstreams")
    switch = sub.add_parser("switch", help="switch an existing branch")
    switch.add_argument("branch")
    branch = sub.add_parser("branch", help="create and switch to a branch")
    branch.add_argument("name")
    branch.add_argument("start", nargs="?")
    push = sub.add_parser("push", help="push using Git's configured upstream")
    push.add_argument("--set-upstream", metavar="REMOTE", help="publish current branch to this remote")
    sub.add_parser("fetch", help="fetch remotes without changing working files")
    wt = sub.add_parser("worktree", help="list/create/remove worktrees").add_subparsers(dest="action")
    wt.add_parser("list")
    new = wt.add_parser("new", help="new branch and worktree")
    new.add_argument("branch")
    new.add_argument("path")
    new.add_argument("--from", dest="start", default="HEAD")
    add = wt.add_parser("add", help="worktree for an existing branch")
    add.add_argument("path")
    add.add_argument("branch")
    remove = wt.add_parser("remove", help="remove a clean worktree; Git refuses dirty worktrees")
    remove.add_argument("path")
    mr = sub.add_parser("mr", help="merge requests").add_subparsers(dest="action")
    mr.add_parser("list")
    create = mr.add_parser("create", help="create a draft merge request")
    create.add_argument("--title")
    create.add_argument("--target")
    for action in ("view", "checkout"):
        item = mr.add_parser(action)
        item.add_argument("id", nargs="?")
    ci = sub.add_parser("ci", help="pipeline status, validation, execution, and logs").add_subparsers(dest="action")
    ci.add_parser("list")
    for action in ("status", "watch", "run"):
        item = ci.add_parser(action)
        item.add_argument("ref", nargs="?", help="branch; defaults to the current branch")
        if action == "run":
            item.add_argument("--variable", action="append", default=[], metavar="KEY:VALUE")
    for action in ("lint", "test"):
        item = ci.add_parser(action, help="validate YAML" if action == "lint" else "simulate pipeline creation; does not execute jobs")
        item.add_argument("file", nargs="?", default=".gitlab-ci.yml")
        if action == "test":
            item.add_argument("--ref", help="branch/tag context for the simulation")
    logs = ci.add_parser("logs", help="stream a job log; omit JOB for glab's picker")
    logs.add_argument("job", nargs="?")
    logs.add_argument("--pipeline", type=int)
    logs.add_argument("--ref")
    # Escape hatches preserve access to the installed tool's complete feature set.
    for name in ("git", "glab"):
        item = sub.add_parser(name, help=f"pass remaining arguments directly to {name}", add_help=False, prefix_chars="+")
        item.add_argument("args", nargs=argparse.REMAINDER)
    return ap


def command_for(a):
    cmd = a.command
    if cmd == "status":
        return ["git", "status", "--short", "--branch"]
    if cmd == "changes":
        return ["git", "diff", *(["--cached"] if a.staged else []), "--", *a.paths]
    if cmd == "stage":
        if not a.paths and not a.all:
            raise ValueError("use stage PATH... or stage --all")
        return ["git", "add", *(["--all"] if a.all else []), "--", *a.paths]
    if cmd == "unstage":
        return ["git", "restore", "--staged", "--", *a.paths]
    if cmd in ("commit", "amend"):
        return ["git", "commit", *(["--amend"] if cmd == "amend" else []),
                *(["-m", a.message] if a.message is not None else (["--no-edit"] if cmd == "amend" else []))]
    if cmd == "log":
        return ["git", "log", "--oneline", "--decorate", "-15"]
    if cmd == "branches":
        return ["git", "branch", "-vv"]
    if cmd == "switch":
        return ["git", "switch", "--", a.branch]
    if cmd == "branch":
        return ["git", "switch", "-c", a.name, "--", *([a.start] if a.start else [])]
    if cmd == "push":
        return ["git", "push", *(["--set-upstream", a.set_upstream, "HEAD"] if a.set_upstream else [])]
    if cmd == "fetch":
        return ["git", "fetch", "--all"]
    if cmd == "worktree":
        if a.action in (None, "list"):
            return ["git", "worktree", "list"]
        if a.action == "new":
            return ["git", "worktree", "add", "-b", a.branch, "--", a.path, a.start]
        if a.action == "add":
            return ["git", "worktree", "add", "--", a.path, a.branch]
        return ["git", "worktree", "remove", "--", a.path]
    if cmd == "mr":
        action = a.action or "list"
        result = ["glab", "mr", action]
        if action == "create":
            result.append("--draft")
            if a.title:
                result += ["--title", a.title]
            if a.target:
                result += ["--target-branch", a.target]
        elif action in ("view", "checkout") and a.id:
            result.append(a.id)
        return result
    if cmd == "ci":
        action = a.action or "status"
        if action == "list":
            return ["glab", "ci", "list"]
        if action in ("status", "watch", "run"):
            result = ["glab", "ci", "run" if action == "run" else "status"]
            if action == "watch":
                result.append("--live")
            if getattr(a, "ref", None):
                result += ["--branch", a.ref]
            for value in getattr(a, "variable", []):
                result += ["--variables-env", value]
            return result
        if action in ("lint", "test"):
            return ["glab", "ci", "lint", a.file,
                    *(["--dry-run", "--include-jobs"] if action == "test" else []),
                    *(["--ref", a.ref] if getattr(a, "ref", None) else [])]
        if action == "logs":
            return ["glab", "ci", "trace", *([a.job] if a.job else []),
                    *(["--pipeline-id", str(a.pipeline)] if a.pipeline is not None else []),
                    *(["--branch", a.ref] if a.ref else [])]
    if cmd in ("git", "glab"):
        return [cmd, *a.args]
    raise ValueError("choose a command; use --help")


def execute(a):
    command = command_for(a)
    if command[0] == "glab" and a.repo:
        command += ["--repo", a.repo]
    print("+ " + shlex.join(command), file=sys.stderr, flush=True)
    if a.dry_run:
        return 0
    if not shutil.which(command[0]):
        raise ValueError(f"{command[0]} is not on PATH; install it or use --dry-run to preview")
    return subprocess.run(command, cwd=a.directory).returncode


def interactive(defaults):
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.completion import NestedCompleter
        from prompt_toolkit.history import FileHistory
    except ImportError:
        raise ValueError("interactive mode needs: python -m pip install prompt_toolkit (direct commands need no Python packages)")
    if defaults.directory:
        os.chdir(defaults.directory)
    home = Path(os.environ.get("LAB_HOME", Path.home() / ".lab"))
    home.mkdir(parents=True, exist_ok=True)
    words = {name: None for name in ("status", "changes", "stage", "unstage", "commit", "amend", "log", "branches", "branch", "switch", "fetch", "push", "cd", "help", "quit")}
    words.update(worktree={x: None for x in ("list", "new", "add", "remove")},
                 mr={x: None for x in ("list", "view", "create", "checkout")},
                 ci={x: None for x in ("status", "watch", "list", "lint", "test", "run", "logs")})
    session = PromptSession(history=FileHistory(str(home / "history")),
                            completer=NestedCompleter.from_nested_dict(words), complete_while_typing=False)
    print("lab — Git and GitLab\nhelp commands · Tab completion · Ctrl+R history · cd PATH switch worktree · quit exit")
    # Startup is local and read-only. Network calls only follow explicit commands.
    execute(argparse.Namespace(command="status", directory=None, dry_run=defaults.dry_run, repo=defaults.repo))
    while True:
        try:
            line = session.prompt(f"lab [{Path.cwd().name}]> ").strip()
            if not line:
                continue
            if line in ("quit", "exit", ":q"):
                return 0
            if line == "help":
                parser().print_help()
                continue
            # shlex retains backslashes inside single-quoted Windows paths.
            args = shlex.split(line)
            if args[0] == "cd":
                if len(args) != 2:
                    raise ValueError("usage: cd PATH (use quotes for spaces)")
                path = Path(args[1]).expanduser().resolve()
                check = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=path, capture_output=True, text=True)
                if check.returncode or check.stdout.strip() != "true":
                    raise ValueError("directory is not a Git working tree")
                os.chdir(path)
                continue
            a = parser().parse_args(args)
            a.repo = a.repo or defaults.repo
            a.dry_run = a.dry_run or defaults.dry_run
            rc = execute(a)
            if rc:
                print(f"lab: command exited with status {rc}", file=sys.stderr)
        except EOFError:
            return 0
        except KeyboardInterrupt:
            print("\nCancelled.")
        except SystemExit:
            # argparse errors should return to the prompt.
            continue
        except (ValueError, OSError) as exc:
            print(f"lab: {exc}", file=sys.stderr)


def main():
    a = parser().parse_args()
    try:
        return execute(a) if a.command else interactive(a)
    except (ValueError, OSError) as exc:
        print(f"lab: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
