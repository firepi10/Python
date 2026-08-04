"""Exercise os/update/bayta-update.sh flow control in a sandbox:
git-channel fetch, atomic symlink flip, health gate, automatic rollback.
Build steps are skipped (BAYTA_SKIP_BUILD) — flow logic is what's under test.
"""

import os
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "os" / "update" / "bayta-update.sh"


@pytest.fixture
def sandbox(tmp_path):
    root = tmp_path / "opt"
    etc = tmp_path / "etc"
    bin_dir = tmp_path / "bin"
    for d in (root / "releases", etc, bin_dir):
        d.mkdir(parents=True)

    # a source repo whose bayta/ dir is what gets "released"
    src = tmp_path / "srcrepo"
    (src / "bayta" / "backend").mkdir(parents=True)
    (src / "bayta" / "VERSION").write_text("9.9.9\n")
    env_git = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

    def git(*args):
        subprocess.run(["git", *args], cwd=src, check=True, capture_output=True, env=env_git)

    git("init", "-q", "-b", "main")
    git("add", ".")
    git("commit", "-q", "-m", "v1")

    # fake systemctl that records calls
    systemctl_log = tmp_path / "systemctl.log"
    fake_systemctl = bin_dir / "fake-systemctl"
    fake_systemctl.write_text(f'#!/bin/bash\necho "$@" >> {systemctl_log}\n')
    fake_systemctl.chmod(fake_systemctl.stat().st_mode | stat.S_IEXEC)

    (etc / "update.conf").write_text(f'REPO_URL="{src}"\nBRANCH="main"\n')

    # current release: a stub the updater should replace
    old = root / "releases" / "old"
    old.mkdir()
    (old / "VERSION").write_text("0.0.1\n")
    (root / "current").symlink_to(old)

    def run(health_ok: bool, extra_env: dict | None = None):
        env = {
            **os.environ,
            "BAYTA_ROOT": str(root),
            "BAYTA_ETC": str(etc),
            "SYSTEMCTL": str(fake_systemctl),
            "HEALTH_CMD": "true" if health_ok else "false",
            "HEALTH_TRIES": "2",
            "BAYTA_SKIP_BUILD": "1",
            **(extra_env or {}),
        }
        return subprocess.run(
            ["bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=120
        )

    return {"root": root, "src": src, "old": old, "run": run, "systemctl_log": systemctl_log,
            "git": git}


def test_update_flips_symlink_on_healthy_release(sandbox):
    result = sandbox["run"](health_ok=True)
    assert result.returncode == 0, result.stderr
    current = (sandbox["root"] / "current").resolve()
    assert current != sandbox["old"]
    assert (current / "VERSION").read_text().strip() == "9.9.9"
    assert (current / ".git-sha").exists()
    assert "restart bayta-backend" in sandbox["systemctl_log"].read_text()


def test_second_run_is_noop(sandbox):
    assert sandbox["run"](health_ok=True).returncode == 0
    result = sandbox["run"](health_ok=True)
    assert result.returncode == 0
    assert "up to date" in result.stderr


def test_failed_health_rolls_back(sandbox):
    result = sandbox["run"](health_ok=False)
    assert result.returncode == 1
    assert "rolling back" in result.stderr
    # symlink restored to the previous release
    assert (sandbox["root"] / "current").resolve() == sandbox["old"]
    # the bad release is quarantined and not retried
    bad = [p for p in (sandbox["root"] / "releases").iterdir() if (p / ".bad").exists()]
    assert len(bad) == 1
    result = sandbox["run"](health_ok=False)
    assert result.returncode == 0
    assert "previously failed" in result.stderr


def test_new_commit_after_rollback_is_tried(sandbox):
    assert sandbox["run"](health_ok=False).returncode == 1
    (sandbox["src"] / "bayta" / "VERSION").write_text("10.0.0\n")
    sandbox["git"]("add", ".")
    sandbox["git"]("commit", "-q", "-m", "v2")
    result = sandbox["run"](health_ok=True)
    assert result.returncode == 0, result.stderr
    assert (sandbox["root"] / "current" / "VERSION").read_text().strip() == "10.0.0"
