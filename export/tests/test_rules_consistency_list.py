"""The shipped rules-consistency list names only repos the kit creates, and public ones.

skills-evals' daily rules-consistency workflow clones every listed repo with no
token. An adopter has no `acsi-kit` repo and, unless they chose a website, no
site repo, so a row for either fails the run every day; a private repo cannot
be cloned without a token. The list must hold only repos from the bootstrap's
own repo set (`FLEET_REPOS` in bootstrap/lib/common.sh) that are never private
(`ALWAYS_PRIVATE`). Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

KIT = Path(__file__).resolve().parents[2]
LIST = KIT / "starter/skills-evals/evals/rules-consistency.yml"
WORKFLOW = KIT / "starter/skills-evals/.github/workflows/rules-consistency.yml"


def bootstrap_array(name: str) -> list[str]:
    out = subprocess.run(
        ["bash", "-c", f'. "$1/bootstrap/lib/common.sh"; printf "%s\\n" "${{{name}[@]}}"', "_", str(KIT)],
        capture_output=True, text=True, check=True)
    return [line for line in out.stdout.splitlines() if line]


def listed() -> list[str]:
    rows = yaml.safe_load(LIST.read_text(encoding="utf-8"))["repos"]
    return [r["repo"] for r in rows]


def test_the_list_names_only_repos_the_kit_creates():
    fleet = set(bootstrap_array("FLEET_REPOS"))
    assert fleet, "could not read FLEET_REPOS"
    names = listed()
    assert names
    for full in names:
        owner, _, repo = full.partition("/")
        assert owner == "example-adopter", full
        assert repo in fleet, f"{full} is not a repo bootstrap/create-repos.sh creates"


def test_the_list_names_no_private_repo_and_never_the_kit():
    private = set(bootstrap_array("ALWAYS_PRIVATE"))
    repos = [full.partition("/")[2] for full in listed()]
    assert not private & set(repos)
    assert "acsi-kit" not in repos
    assert not any(r.startswith("example-site") for r in repos)


def test_the_clone_failure_says_the_repo_must_be_public():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "could not clone $repo (cloned with no token: it must be public" in text
