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


def test_the_shipped_list_marks_where_skills_evals_goes():
    # The comment kit_repos.py writes begins with the words coverage_fleet.py looks for.
    text = REPOS_YML.read_text(encoding="utf-8")
    assert text.count(f"    # skills-evals {cf.MARKER}") == 1


def test_the_evals_state_puts_skills_evals_where_the_comment_was_and_says_nothing_stale():
    before = REPOS_YML.read_text(encoding="utf-8")
    after = cf.add(before, "skills-evals")
    names = cf.names(before)
    at = names.index("repo-settings") + 1                  # where the source lists it
    assert cf.names(after) == names[:at] + ["skills-evals"] + names[at:]
    assert cf.MARKER not in after and "in place of" not in after        # the file no longer says it is not listed
    want = yaml.safe_load(before)
    want["cron_coverage"]["fleet"].insert(at, "skills-evals")
    assert yaml.safe_load(after) == want
    # One line in, the comment's lines out, and every other line as it was.
    gone = [l for l in before.split("\n") if l not in after.split("\n")]
    assert all(l.strip().startswith("#") for l in gone) and gone[0].strip().startswith("# skills-evals " + cf.MARKER)
    assert [l for l in after.split("\n") if l not in before.split("\n")] == ["    - skills-evals"]
    assert cf.add(after, "skills-evals") == after          # a second add changes nothing


def test_the_commands_report_both_states(tmp_path, capsys):
    f = tmp_path / "repos.yml"
    f.write_bytes(REPOS_YML.read_bytes())
    assert cf.main(["check", str(f), "owner/_agent-guidance repos.yml", "skills-evals"]) == 1
    assert capsys.readouterr().out == "NOT DONE: owner/_agent-guidance repos.yml cron_coverage.fleet does not name skills-evals\n"
    assert cf.main(["add", str(f), "owner/_agent-guidance repos.yml", "skills-evals"]) == 0
    assert cf.main(["check", str(f), "owner/_agent-guidance repos.yml", "skills-evals"]) == 0


# ---------------------------------------------------------------- invented files

def test_without_a_marker_the_name_goes_after_the_last_element_and_comments_stay():
    assert cf.add(SMALL, "three") == SMALL.replace("    - two   # the last one\n", "    - two   # the last one\n    - three\n")


MARKED = """\
cron_coverage:
  fleet:
    - one
    # a comment about one stays
    - two
    # three is not listed while you have no such repo: some reason,
    # continued on a second line.
    - zebra   # trailing
  # after the list
  out_of_scope: []
"""


def test_the_name_replaces_its_marker_comment_and_only_that():
    after = cf.add(MARKED, "three")
    assert after == MARKED.replace("    # three is not listed while you have no such repo: some reason,\n"
                                   "    # continued on a second line.\n", "    - three\n")
    assert cf.names(after) == ["one", "two", "three", "zebra"]
    assert cf.add(after, "three") == after


def test_a_marker_for_another_name_is_left_alone():
    after = cf.add(MARKED, "four")
    assert cf.names(after) == ["one", "two", "zebra", "four"] and "# three is not listed while" in after


def test_a_marker_under_the_last_element_is_replaced_too():
    text = "cron_coverage:\n  fleet:\n    - one\n    # two is not listed while it does not exist.\n  out_of_scope: []\n"
    assert cf.add(text, "two") == "cron_coverage:\n  fleet:\n    - one\n    - two\n  out_of_scope: []\n"


@pytest.mark.parametrize("next_comment", ["  # the next key's comment\n", "# a top-level comment\n"])
def test_the_next_keys_comment_right_under_the_marker_stays(next_comment):
    # The marker sits right under the last element, and the next key's comment
    # follows with no blank line: that comment is the next key's, at a lesser
    # indent than the list, and must survive the add.
    text = ("cron_coverage:\n  fleet:\n    - one\n    # two is not listed while it does not exist.\n"
            "    # continued.\n" + next_comment + "  out_of_scope: []\n")
    want = "cron_coverage:\n  fleet:\n    - one\n    - two\n" + next_comment + "  out_of_scope: []\n"
    assert cf.add(text, "two") == want


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
