"""Runs the real .githooks/pre-push against throwaway repos.

On 2026-11-24 the hook let a new 3-commit branch through without running the
pipeline check and without saying so: `git diff-tree` given three commits
reads the third as a path and lists no files. These cases pin down when the
hook runs the check, and that it never skips silently.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / ".githooks" / "pre-push"
ZERO = "0" * 40
STUB = '#!/usr/bin/env bash\necho "STUB CHECK RAN"\nexit "${STUB_EXIT:-0}"\n'


def _env(**extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(extra)
    return env


def _git(cwd, *args):
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd, check=True, capture_output=True, text=True, env=_env(),
    ).stdout.strip()


def _commit(repo, rel, text="x\n"):
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", f"touch {rel}")
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path):
    """A clone whose main is on origin, with a stub check-pipeline.sh."""
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    work = tmp_path / "work"
    _git(tmp_path, "clone", "-q", str(origin), str(work))
    _commit(work, "scripts/check-pipeline.sh", STUB)
    _git(work, "push", "-q", "origin", "HEAD:main")
    _git(work, "checkout", "-qb", "feature")
    return work


def _run_hook(repo, local_sha, remote_sha, **env):
    bash = shutil.which("bash")
    assert bash, "bash is needed to run the hook"
    # Bytes, not text: text mode on Windows would send CRLF, which git never does.
    line = f"refs/heads/feature {local_sha} refs/heads/feature {remote_sha}\n".encode()
    result = subprocess.run(
        [bash, str(HOOK), "origin", "unused"], cwd=repo, input=line,
        capture_output=True, env=_env(**env),
    )
    return subprocess.CompletedProcess(
        result.args, result.returncode,
        result.stdout.decode(errors="replace"), result.stderr.decode(errors="replace"),
    )


def test_new_branch_of_three_commits_runs_the_check(repo):
    _commit(repo, "backend/a.py")
    _commit(repo, "frontend/b.ts")
    head = _commit(repo, "frontend/c.ts")
    result = _run_hook(repo, head, ZERO)
    assert result.returncode == 0, result.stderr
    assert "STUB CHECK RAN" in result.stdout


def test_new_branch_change_in_any_commit_counts(repo):
    _commit(repo, "frontend/b.ts")
    head = _commit(repo, "scripts/tests/t.py")
    assert "STUB CHECK RAN" in _run_hook(repo, head, ZERO).stdout


def test_existing_branch_runs_the_check(repo):
    base = _commit(repo, "frontend/b.ts")
    head = _commit(repo, ".github/workflows/w.yml")
    assert "STUB CHECK RAN" in _run_hook(repo, head, base).stdout


def test_frontend_only_push_says_why_it_skips(repo):
    head = _commit(repo, "frontend/b.ts")
    result = _run_hook(repo, head, ZERO)
    assert result.returncode == 0
    assert "STUB CHECK RAN" not in result.stdout
    assert "pipeline check not needed" in result.stdout


def test_unknown_remote_commit_runs_the_check(repo):
    head = _commit(repo, "frontend/b.ts")
    result = _run_hook(repo, head, "1" * 40)
    assert "STUB CHECK RAN" in result.stdout


def test_failed_check_blocks_the_push(repo):
    head = _commit(repo, "backend/a.py")
    result = _run_hook(repo, head, ZERO, STUB_EXIT="3")
    assert result.returncode != 0
    assert "push blocked" in result.stderr


def test_missing_check_script_blocks_the_push(repo):
    (repo / "scripts" / "check-pipeline.sh").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "drop check")
    head = _commit(repo, "backend/a.py")
    result = _run_hook(repo, head, ZERO)
    assert result.returncode != 0
    assert "is missing" in result.stderr
