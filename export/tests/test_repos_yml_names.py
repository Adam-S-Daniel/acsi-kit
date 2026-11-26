"""The shipped `_agent-guidance` repos.yml names only the kit's repos, comments included.

`export/patches/_agent-guidance/kit_repos.py` cuts the source owner's other
repos from the lists (DECISIONS C11) and holds the YAML values to
`kit_repos`. The header's note on forks once named two of the source owner's
forks as "the current forks"; the patch now rewords it and holds every
owner-qualified name in the file's text, a lexical token, to the kit's repos.

Run: python3 -m pytest export/tests/test_repos_yml_names.py -q
"""

import importlib.util
import re
from pathlib import Path

import pytest
import yaml

KIT = Path(__file__).resolve().parents[2]
REPOS_YML = KIT / "starter/agent-guidance/repos.yml"
COMMON = yaml.safe_load((KIT / "export/manifests/_common.yml").read_text(encoding="utf-8"))
_spec = importlib.util.spec_from_file_location("kit_repos", KIT / "export/patches/_agent-guidance/kit_repos.py")
kit_repos = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kit_repos)


KIT_REPOS = set(COMMON["kit_repos"])


def test_every_owner_qualified_name_in_the_shipped_file_is_a_kit_repo():
    assert kit_repos.names_outside_kit(REPOS_YML.read_text(encoding="utf-8"), KIT_REPOS) == []


def test_the_note_on_forks_keeps_the_rule_and_names_no_fork():
    text = REPOS_YML.read_text(encoding="utf-8")
    assert "FORKS. Discovery passes `--source`" in text
    assert "To sync a fork, it would have to stop being a fork" in text
    assert "the current forks" not in text


@pytest.mark.parametrize("line, stray", [
    ("# example-adopter/some-fork is a fork\n", ["some-fork"]),
    ("#   see example-adopter-two/Other.Repo and example-adopter/wsl-automation\n", ["Other.Repo"]),
    ("# example-adopter/retired-agentskills was retired\n", []),
    ("# someone-else/their-repo is not the owner's\n", []),
])
def test_the_patchs_check_reads_comments(line, stray):
    # The check apply() ends with: a name outside the kit stops the export.
    assert kit_repos.names_outside_kit(REPOS_YML.read_text(encoding="utf-8") + line, KIT_REPOS) == stray
