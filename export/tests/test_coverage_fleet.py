"""`cron_coverage.fleet` in the shipped repos.yml, without and with skills-evals.

The guidance starter's list leaves `skills-evals` out: a base-only setup has
no such repo, and `dependabot-config-health.yml` fails every day on a name
neither owner has (export/DECISIONS.md, "Pro plan values and small fixes").
`bootstrap/regenerate.sh evals-fleet` adds it with
`bootstrap/lib/coverage_fleet.py` once the evals track has created the repo.
These tests hold both states: the shipped list, and the list after the add.

Run: python3 -m pytest export/tests/test_coverage_fleet.py -q
"""

import importlib.util
from pathlib import Path

import pytest
import yaml

KIT = Path(__file__).resolve().parents[2]
REPOS_YML = KIT / "starter/agent-guidance/repos.yml"
COMMON = yaml.safe_load((KIT / "export/manifests/_common.yml").read_text(encoding="utf-8"))
_spec = importlib.util.spec_from_file_location("coverage_fleet", KIT / "bootstrap/lib/coverage_fleet.py")
cf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cf)

SMALL = """\
# head
cron_coverage:
  # the audited repos
  fleet:
    - one
    - two   # the last one
  # after the list
  out_of_scope: []
other: 1
"""


# ---------------------------------------------------------------- the shipped file

def test_the_shipped_list_names_kit_repos_and_not_skills_evals():
    names = cf.names(REPOS_YML.read_text(encoding="utf-8"))
    assert "skills-evals" not in names
    assert set(names) <= set(COMMON["kit_repos"]) and "_agent-guidance" in names


def test_the_evals_state_is_the_shipped_list_plus_skills_evals_and_nothing_else():
    before = REPOS_YML.read_text(encoding="utf-8")
    after = cf.add(before, "skills-evals")
    assert cf.names(after) == cf.names(before) + ["skills-evals"]
    want = yaml.safe_load(before)
    want["cron_coverage"]["fleet"].append("skills-evals")
    assert yaml.safe_load(after) == want
    assert len(after.split("\n")) == len(before.split("\n")) + 1
    assert cf.add(after, "skills-evals") == after          # a second add changes nothing


def test_the_commands_report_both_states(tmp_path, capsys):
    f = tmp_path / "repos.yml"
    f.write_bytes(REPOS_YML.read_bytes())
    assert cf.main(["check", str(f), "owner/_agent-guidance repos.yml", "skills-evals"]) == 1
    assert capsys.readouterr().out == "NOT DONE: owner/_agent-guidance repos.yml cron_coverage.fleet does not name skills-evals\n"
    assert cf.main(["add", str(f), "owner/_agent-guidance repos.yml", "skills-evals"]) == 0
    assert cf.main(["check", str(f), "owner/_agent-guidance repos.yml", "skills-evals"]) == 0


# ---------------------------------------------------------------- invented files

def test_the_name_goes_after_the_last_element_and_comments_stay():
    assert cf.add(SMALL, "three") == SMALL.replace("    - two   # the last one\n", "    - two   # the last one\n    - three\n")


@pytest.mark.parametrize("text, said", [
    ("cron_coverage:\n  fleet: [one, two]\n", "no cron_coverage.fleet block list"),
    ("cron_coverage:\n  fleet: []\n", "no cron_coverage.fleet block list"),
    ("cron_coverage:\n  out_of_scope: []\n", "no cron_coverage.fleet block list"),
    ("other: 1\n", "no cron_coverage.fleet block list"),
    ("cron_coverage:\n  fleet:\n    - {repo: one}\n", "not a plain repo name"),
    ("cron_coverage:\n  fleet:\n    - one\n   - two\n", "not valid YAML"),
    ('cron_coverage:\n  fleet:\n    - "one"\n', "a form this cannot extend"),
])
def test_a_list_of_another_shape_is_an_error(text, said):
    with pytest.raises(cf.ShapeError) as e:
        cf.add(text, "three")
    assert said in str(e.value)


def test_a_refused_add_leaves_the_file_as_it_was(tmp_path, capsys):
    f = tmp_path / "repos.yml"
    f.write_text("cron_coverage:\n  fleet: [one]\n", encoding="utf-8")
    assert cf.main(["add", str(f), "label", "two"]) == 2
    assert f.read_text(encoding="utf-8") == "cron_coverage:\n  fleet: [one]\n"
    assert capsys.readouterr().err.startswith("ERROR: label: has no cron_coverage.fleet block list")
    assert cf.main(["add", str(f), "label", "not a name"]) == 2
