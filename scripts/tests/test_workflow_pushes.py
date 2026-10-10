"""Replays every workflow step that pushes to main against a throwaway remote.

The pipeline's bot commits run on a runner nobody watches, after jobs that
rewrite tracked files they do not commit (run_build.py rewrites
training_data.parquet), while main may have moved underneath them. On
2026-10-10 a step that passed review failed exactly there: `git pull --rebase`
refused to run over the dirty parquet, the retrain never landed and the
chain stopped. This runs each such step's own script under those conditions,
so the next one fails on the developer's machine instead of on a Sunday.
"""

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))

# A tracked file the job rewrites but does not commit, like training_data.parquet.
BYSTANDER = "bystander/tracked_output.bin"
UPSTREAM = "upstream/someone_elses_change.txt"


def _pushing_steps():
    for wf in WORKFLOWS:
        jobs = yaml.safe_load(wf.read_text(encoding="utf-8")).get("jobs", {})
        for job in jobs.values():
            for step in job.get("steps", []):
                script = step.get("run", "")
                if "git push" in script:
                    yield pytest.param(script, id=f"{wf.name}: {step.get('name', '?')}")


def _added_paths(script):
    """The paths a step stages: the arguments of every `git add`."""
    paths = []
    for line in script.replace("\\\n", " ").splitlines():
        words = shlex.split(line, comments=True)
        if words[:2] == ["git", "add"]:
            paths += [w for w in words[2:] if not w.startswith("-")]
    return paths


def _git(cwd, *args):
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    ).stdout


def _write(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.mark.parametrize("script", list(_pushing_steps()))
def test_bot_push_survives_moved_main_and_dirty_tree(script, tmp_path):
    bash = shutil.which("bash")
    assert bash, "bash is needed to run workflow steps"
    owned = _added_paths(script)
    assert owned, "a pushing step should stage explicit paths, not everything"

    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))

    seed = tmp_path / "seed"
    _git(tmp_path, "clone", "-q", str(origin), str(seed))
    for rel in [*owned, BYSTANDER]:
        _write(seed, rel, "v1\n")
    _git(seed, "add", "-A")
    _git(seed, "commit", "-qm", "seed")
    _git(seed, "push", "-q", "origin", "HEAD:main")

    runner = tmp_path / "runner"
    _git(tmp_path, "clone", "-q", str(origin), str(runner))

    # Someone pushes while the job runs.
    _write(seed, UPSTREAM, "landed mid-run\n")
    _git(seed, "add", "-A")
    _git(seed, "commit", "-qm", "upstream")
    _git(seed, "push", "-q", "origin", "HEAD:main")

    # The job's outputs: its own files plus a tracked file it does not commit.
    for rel in [*owned, BYSTANDER]:
        _write(runner, rel, "v2\n")

    step = tmp_path / "step.sh"
    step.write_text(script, encoding="utf-8")
    result = subprocess.run(
        [bash, "-e", str(step)], cwd=runner, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    log = _git(origin, "log", "--format=%s", "main")
    assert "upstream" in log, "the bot's push dropped a commit from main"
    pushed = set(_git(origin, "show", "--name-only", "--format=", "main").split())
    assert pushed == set(owned), "the bot commit should touch only its own files"
