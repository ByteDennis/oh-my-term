import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).parents[1] / "lab.py"


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
    return root


def lab(repo, *args, env=None):
    return subprocess.run([sys.executable, str(SCRIPT), "-C", str(repo), *args],
                          capture_output=True, text=True, env=env)


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def test_commit_amend_and_unstaged_files_are_preserved(repo):
    (repo / "selected file.txt").write_text("first")
    (repo / "unrelated.txt").write_text("preserve")
    assert lab(repo, "stage", "selected file.txt").returncode == 0
    message = "literal $(touch BAD) `whoami` 'quoted'"
    assert lab(repo, "commit", "-m", message).returncode == 0
    assert git(repo, "log", "-1", "--format=%s") == message
    assert not (repo / "BAD").exists()
    old = git(repo, "rev-parse", "HEAD")
    (repo / "selected file.txt").write_text("amended")
    assert lab(repo, "stage", "selected file.txt").returncode == 0
    assert lab(repo, "amend").returncode == 0
    assert git(repo, "rev-parse", "HEAD") != old
    assert git(repo, "rev-list", "--count", "HEAD") == "1"
    assert "?? unrelated.txt" in git(repo, "status", "--short")
    assert not git(repo, "remote")


def test_branch_and_worktree_lifecycle(repo, tmp_path):
    (repo / "base").write_text("base")
    assert lab(repo, "stage", "base").returncode == 0
    assert lab(repo, "commit", "-m", "base").returncode == 0
    assert lab(repo, "branch", "feature").returncode == 0
    assert lab(repo, "switch", "main").returncode == 0
    path = tmp_path / "worktree with spaces"
    result = lab(repo, "worktree", "new", "parallel", str(path))
    assert result.returncode == 0, result.stderr
    assert git(path, "branch", "--show-current") == "parallel"
    (path / "dirty").write_text("keep")
    assert lab(repo, "worktree", "remove", str(path)).returncode != 0
    assert (path / "dirty").exists()
    (path / "dirty").unlink()
    assert lab(repo, "worktree", "remove", str(path)).returncode == 0


def test_stage_requires_paths_and_dry_run_does_not_modify(repo):
    (repo / "keep").write_text("keep")
    assert lab(repo, "stage").returncode != 0
    assert lab(repo, "--dry-run", "stage", "--all").returncode == 0
    assert not git(repo, "diff", "--cached", "--name-only")
    assert lab(repo, "--dry-run", "glab", "--help").returncode == 0
    assert lab(repo, "git", "-c", "color.ui=false", "status", "--short").returncode == 0


def test_self_hosted_ci_routing_and_exit_codes(repo, tmp_path):
    # A recording executable substitutes only glab. Git workflows above are real.
    bindir = tmp_path / "bin"
    bindir.mkdir()
    stub = bindir / "glab"
    stub.write_text(f'#!{sys.executable}\nimport json, os, sys\n'
                    'open(os.environ["CALLS"], "a").write(json.dumps(sys.argv[1:]) + "\\n")\n'
                    'sys.exit(int(os.environ.get("STUB_EXIT", "0")))\n')
    stub.chmod(0o755)
    calls = tmp_path / "calls"
    env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ["PATH"], CALLS=str(calls))
    remote = "https://gitlab.company.example/team/project"
    assert lab(repo, "--repo", remote, "ci", "test", "--ref", "feature", env=env).returncode == 0
    assert lab(repo, "--repo", remote, "ci", "run", "feature", "--variable", "MODE:test", env=env).returncode == 0
    assert lab(repo, "ci", "logs", "123", "--pipeline", "456", env=env).returncode == 0
    values = [json.loads(line) for line in calls.read_text().splitlines()]
    assert values[0] == ["ci", "lint", ".gitlab-ci.yml", "--dry-run", "--include-jobs", "--ref", "feature", "--repo", remote]
    assert values[1] == ["ci", "run", "--branch", "feature", "--variables-env", "MODE:test", "--repo", remote]
    assert values[2] == ["ci", "trace", "123", "--pipeline-id", "456"]
    assert lab(repo, "ci", "status", env=dict(env, STUB_EXIT="7")).returncode == 7
