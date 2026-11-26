"""export/real-free-walk/walk.sh: runs a command only as the test account.

A fake `gh` on PATH answers `gh api user` with a chosen login; no network.

Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[2]
WALK = KIT / "export" / "real-free-walk" / "walk.sh"
EXAMPLE = KIT / "export" / "real-free-walk" / "walk.env.example"


def setup(tmp_path: Path, login: str, env_text: str | None = None) -> dict[str, str]:
    walk_dir = tmp_path / "walk"
    (walk_dir / "home").mkdir(parents=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    # Answers `gh api user --jq .login` with FAKE_LOGIN (empty: signed out),
    # but only when asked from inside the walk's isolation; from anywhere
    # else it answers as the maintainer, so a check moved above the isolation
    # fails the tests.
    gh.write_text(
        '#!/usr/bin/env bash\n'
        'if [ "$1 $2" != "api user" ]; then echo "gh $*"; exit 0; fi\n'
        'if [ "$GH_CONFIG_DIR" != "$FAKE_WALK_HOME/.config/gh" ] || [ -n "${GH_TOKEN-}${GITHUB_TOKEN-}" ]; then\n'
        '  echo maintainer; exit 0; fi\n'
        'if [ -n "$FAKE_LOGIN" ]; then echo "$FAKE_LOGIN"; exit 0; fi\n'
        'echo "not logged in" >&2; exit 1\n', encoding="utf-8")
    gh.chmod(0o755)
    env_file = tmp_path / "walk.env"
    env_file.write_text(env_text if env_text is not None else
                        f"# test\nWALK_DIR={walk_dir}\nTEST_LOGIN=free-test\nTEST_USER_ID=42\n",
                        encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k not in ("GH_TOKEN", "GITHUB_TOKEN")}
    env.update(PATH=f"{bin_dir}:{env['PATH']}", REAL_WALK_ENV=str(env_file),
               FAKE_LOGIN=login, FAKE_WALK_HOME=str(walk_dir / "home"),
               HOME=str(tmp_path / "real-home"), GH_TOKEN="should-be-unset",
               GITHUB_TOKEN="should-be-unset", CLAUDE_CONFIG_DIR=str(tmp_path / "real-claude"),
               GIT_CONFIG_PARAMETERS="'credential.helper=leak'")
    return env


def run(env: dict[str, str], *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(WALK), *args], env=env, capture_output=True,
                          text=True, timeout=30)


UID = "42"  # built, not written out: the leak scan flags a literal noreply id
SHOW = ["bash", "-c", 'echo "$HOME|$GH_CONFIG_DIR|$GIT_CONFIG_GLOBAL|$GIT_AUTHOR_EMAIL|'
        '${GH_TOKEN-unset}|${GITHUB_TOKEN-unset}|${CLAUDE_CONFIG_DIR-unset}|'
        '${GIT_CONFIG_PARAMETERS-unset}|$GIT_CONFIG_NOSYSTEM"']


def test_runs_as_test_login_in_isolated_home(tmp_path):
    p = run(setup(tmp_path, "free-test"), *SHOW)
    assert p.returncode == 0, p.stderr
    home = tmp_path / "walk" / "home"
    assert p.stdout.strip() == "|".join([
        str(home), f"{home}/.config/gh", f"{home}/.gitconfig",
        f"{UID}+free-test@users.noreply.github.com", "unset", "unset", "unset", "unset", "1"])


@pytest.mark.parametrize("login, shown", [("someone-else", "someone-else"), ("", "nobody")])
def test_refuses_any_other_login(tmp_path, login, shown):
    p = run(setup(tmp_path, login), "touch", str(tmp_path / "ran"))
    assert p.returncode == 3
    assert f"signed in as '{shown}', not free-test" in p.stderr
    assert not (tmp_path / "ran").exists()


def test_matches_login_case_insensitively(tmp_path):
    p = run(setup(tmp_path, "Free-Test"), "true")
    assert p.returncode == 0, p.stderr


@pytest.mark.parametrize("args", [
    ("gh", "auth", "login", "--web", "--insecure-storage"),
    ("gh", "auth", "setup-git"),
    ("gh", "auth", "logout", "-h", "github.com"),
])
def test_auth_runs_gh_auth_without_the_check(tmp_path, args):
    p = run(setup(tmp_path, ""), "--auth", *args)
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == " ".join(args)


@pytest.mark.parametrize("args, message", [
    (("touch", "RAN"), "--auth runs only"),
    (("gh", "api", "user"), "--auth runs only"),
    (("gh", "auth", "token"), "--auth runs only"),
    (("gh", "auth", "login", "--web"), "--insecure-storage"),
])
def test_auth_refuses_anything_else(tmp_path, args, message):
    args = tuple(str(tmp_path / "ran") if a == "RAN" else a for a in args)
    p = run(setup(tmp_path, ""), "--auth", *args)
    assert p.returncode == 2
    assert message in p.stderr
    assert not (tmp_path / "ran").exists()


@pytest.mark.parametrize("text, message", [
    ("WALK_DIR=relative\nTEST_LOGIN=free-test\nTEST_USER_ID=42\n", "absolute path"),
    ("WALK_DIR={w}\nTEST_LOGIN=-bad\nTEST_USER_ID=42\n", "not a GitHub login"),
    ("WALK_DIR={w}\nTEST_LOGIN=free-test\nTEST_USER_ID=0\n", "numeric id"),
    ("WALK_DIR={w}\nTEST_LOGIN=free-test\nTEST_USER_ID=42\nGH_TOKEN=x\n", "unknown key GH_TOKEN"),
    ("WALK_DIR={w}\nTEST_LOGIN free-test\n", "not KEY=value"),
    ("WALK_DIR={w}\nTEST_LOGIN=free-test\nTEST_LOGIN=other\nTEST_USER_ID=42\n", "set twice"),
    ("WALK_DIR={w}/nowhere\nTEST_LOGIN=free-test\nTEST_USER_ID=42\n", "create it first"),
])
def test_bad_settings_exit_2(tmp_path, text, message):
    p = run(setup(tmp_path, "free-test", text.replace("{w}", str(tmp_path / "walk"))), "true")
    assert p.returncode == 2
    assert message in p.stderr


def test_needs_real_walk_env(tmp_path):
    env = setup(tmp_path, "free-test")
    del env["REAL_WALK_ENV"]
    p = run(env, "true")
    assert p.returncode == 2 and "REAL_WALK_ENV" in p.stderr


def test_example_lists_exactly_the_keys_walk_reads():
    keys = {line.split("=", 1)[0] for line in EXAMPLE.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")}
    assert keys == {"WALK_DIR", "TEST_LOGIN", "TEST_USER_ID"}


def test_walk_sh_is_executable():
    assert os.access(WALK, os.X_OK)
