# lab

A compact command layer over Git and your installed `glab`, with an interactive
prompt, history, completion, worktrees, merge requests and CI workflows.

## Install

Requires Python 3.10+, Git, and `glab`. For the interactive prompt:

```bash
python -m pip install --user prompt_toolkit
export PATH="$HOME/oh-my-term/lab:$PATH"
cd /path/to/your/company-repository
lab
```

Use the actual checkout path in `PATH`. Git Bash on Windows is supported; put
the directory on `PATH` rather than copying the launcher. Set `LAB_PYTHON=py`
if `python` opens the Microsoft Store. Direct commands use only Python's
standard library; `glab` is needed only for GitLab operations.

The tool inherits glab's configured authentication and derives the GitLab host
from the current repository. It stores no credentials. When needed, glab's
normal `glab auth login --hostname gitlab.company.example` configures a company
instance. `lab --repo https://gitlab.company.example/group/project ci status`
overrides the project for GitLab commands. Local Git operations still operate
on the current directory (or the global `-C PATH` argument).

## Everyday workflow

```bash
lab status
lab changes
lab stage src/app.py
lab changes --staged
lab commit -m "Describe the change"
lab amend                      # staged changes, same message, no push
lab amend -m "Better message"
lab push                       # normal Git push, using configured upstream
lab push --set-upstream origin # publish current branch
lab mr create --title "Describe the change" --target main
```

Commits only include changes you staged. Amend rewrites the current local
commit; it never force-pushes. Commands print the actual Git/glab invocation.
Use `lab --dry-run ...` to preview any command without executing it. Arguments
are passed directly, never evaluated as shell code.

## Worktrees and branches

```bash
lab branches
lab branch feature/refactor
lab switch main
lab worktree list
lab worktree new feature/fix ../project-fix --from main
lab worktree add ../existing-feature existing-feature
lab worktree remove ../project-fix
```

Removal uses Git's normal clean-worktree checks. In the interactive prompt,
`cd ../project-fix` switches the tool's working directory. An external program
cannot change the parent terminal's directory; outside the prompt, use shell
`cd` or `lab -C ../project-fix status`.

## Pipelines

| Command | Behavior |
|---|---|
| `lab ci` / `lab ci status [BRANCH]` | Current branch's pipeline status |
| `lab ci list` | Recent pipelines |
| `lab ci watch [BRANCH]` | Live status until the pipeline ends |
| `lab ci logs [JOB] --pipeline ID` | Stream a job log, or use glab's job picker |
| `lab ci lint [FILE]` | Validate CI YAML on the GitLab server |
| `lab ci test [FILE] --ref BRANCH` | Simulate pipeline creation and list jobs; does not execute them |
| `lab ci run [BRANCH] --variable MODE:test` | Start an actual remote pipeline |

`ci run` uses the repository state already on GitLab; it does not upload local
edits, commit or push. `ci lint/test` send the local YAML to GitLab's lint API;
includes and rule evaluation depend on the server/ref context. Neither runs
job scripts locally. Older glab/GitLab releases may not support lint simulation;
the underlying error and exit status are preserved.

The prompt starts with local Git status; network operations follow explicit
commands. Tab completes commands and Ctrl+R searches persistent history in
`~/.lab/history` (`LAB_HOME` overrides it). `help` shows commands, `quit` exits.
History is local plaintext; use environment-based credentials in glab rather
than typing secrets into commands. `lab git ...` and `lab glab ...` expose
additional underlying commands unchanged. `lab glab --help` shows glab help.

Reference: [glab CI run](https://docs.gitlab.com/cli/ci/run/),
[lint and simulation](https://docs.gitlab.com/cli/ci/lint/),
[live status](https://docs.gitlab.com/cli/ci/status/),
[job logs](https://docs.gitlab.com/cli/ci/trace/).
