"""owner_forms.py: the names and edits run_suites.py gives a copy before its suite runs.

The "drop the example repos" transform must find the rows by their node
positions, take each row's own comment with it, leave every other byte alone,
and fail loudly when the rows are not there.

Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent
EXPORT_DIR = HERE.parent
KIT = EXPORT_DIR.parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, mod)
    spec.loader.exec_module(mod)
    return mod


owner_forms = _load("kit_owner_forms", EXPORT_DIR / "owner_forms.py")
substitute = _load("kit_substitute_for_forms", KIT / "bootstrap" / "lib" / "substitute.py")

FLEET = """\
defaults:
  a: 1

repos:
  - name: example-adopter/repo-settings
    manage: ["all"]

  # --- the example repos: why they are here
  #     (a second line of the same note) ---
  - name: example-adopter/example-site-platform
    manage: ["labels"]
  - name: example-adopter/example-site-a
    manage: ["labels"]
  - name: example-adopter-two/example-site-b
    manage: ["labels"]
"""


def test_the_forms_use_names_the_substitution_accepts():
    for form, (owner, owner_two, name, noreply) in owner_forms.FORMS.items():
        assert substitute.LOGIN.fullmatch(owner) and substitute.LOGIN.fullmatch(owner_two), form
        assert substitute.NAME.fullmatch(name), form
        assert substitute.NOREPLY.fullmatch(noreply), form
    one, two = owner_forms.FORMS["one"], owner_forms.FORMS["two"]
    # One account, spelled in two cases; two accounts that sort the other way
    # round from the invented pair.
    assert one[0].lower() == one[1].lower() and one[0] != one[1]
    assert sorted([two[0].lower(), two[1].lower()]) == [two[1].lower(), two[0].lower()]
    assert two[0].lower() > two[1].lower()


def test_each_adopter_form_has_a_time_zone_that_is_not_the_exports():
    import zoneinfo
    time_zone = _load("kit_time_zone_for_forms", KIT / "bootstrap" / "lib" / "time_zone.py")
    assert set(owner_forms.ZONES) == set(owner_forms.FORMS)
    for form, zone in owner_forms.ZONES.items():
        assert zone != "UTC" and time_zone.SHAPE.fullmatch(zone), form
        zoneinfo.ZoneInfo(zone)


def test_stage_gives_the_names_the_zone_and_then_the_digests(tmp_path):
    # What copy-starter.sh does to a staged tree, in its order: the names, the
    # zone, then the digests of the files as those steps left them.
    import hashlib
    (tmp_path / "scripts").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    window = tmp_path / "scripts" / "base-md-merge-window.yml"
    window.write_text("timezone: UTC\nweekday: 1\n")
    hook = tmp_path / ".claude" / "hooks" / "fleet-memory.sh"
    hook.write_text("echo example-adopter\n")
    (tmp_path / "docs" / "codex-cloud.md").write_text("fleet_pin_sha256=" + "0" * 64 + "\n")
    owner_forms.stage(tmp_path, "agent-guidance-like", "one")
    assert window.read_text() == f"timezone: {owner_forms.ZONES['one']}\nweekday: 1\n"
    assert hook.read_text() == "echo acme-solo\n"
    want = hashlib.sha256(hook.read_bytes()).hexdigest()
    assert (tmp_path / "docs" / "codex-cloud.md").read_text() == f"fleet_pin_sha256={want}\n"


def test_the_example_rows_go_with_their_comment_and_the_trailing_blank_line():
    out = owner_forms.drop_example_rows(FLEET, ["repos"], 3)
    assert out == "defaults:\n  a: 1\n\nrepos:\n  - name: example-adopter/repo-settings\n    manage: [\"all\"]\n"
    assert yaml.safe_load(out)["repos"] == [{"name": "example-adopter/repo-settings", "manage": ["all"]}]


def test_a_row_in_the_middle_leaves_the_rest_byte_for_byte():
    text = ("repos:\n"
            "  - name: o/keep-1\n"
            "  # the note on the example repo\n"
            "  - name: o/example-site-a\n"
            "    manage: []\n"
            "\n\n"
            "  - name: o/keep-2\n"
            "    manage: []\n")
    out = owner_forms.drop_example_rows(text, ["repos"], 1)
    assert out == "repos:\n  - name: o/keep-1\n\n\n  - name: o/keep-2\n    manage: []\n"


def test_scalar_lists_are_cut_by_value_and_a_block_cut_between_blanks_leaves_one():
    text = ("top:\n  lst:\n    # keep note\n    - a\n\n    # lock: the example's note\n    - example-site-x\n\n    - b\n"
            "other:\n    - example-site-y\n")
    out = owner_forms.drop_example_rows(text, ["top", "lst"], 1)
    assert yaml.safe_load(out) == {"top": {"lst": ["a", "b"]}, "other": ["example-site-y"]}
    assert out == "top:\n  lst:\n    # keep note\n    - a\n\n    - b\nother:\n    - example-site-y\n"


def test_a_missing_row_or_list_fails_loudly():
    with pytest.raises(owner_forms.FormError, match="expected 4 .*found 3"):
        owner_forms.drop_example_rows(FLEET, ["repos"], 4)
    with pytest.raises(owner_forms.FormError, match="no `nope`"):
        owner_forms.drop_example_rows(FLEET, ["nope"], 1)
    with pytest.raises(owner_forms.FormError, match="not a block list"):
        owner_forms.drop_example_rows("repos: [example-site-a]\n", ["repos"], 1)
    with pytest.raises(owner_forms.FormError, match="expected 1 .*found 0"):
        owner_forms.drop_example_rows("repos:\n  - name: o/real\n", ["repos"], 1)


def test_only_a_repo_name_that_starts_with_the_prefix_is_an_example_row():
    text = "repos:\n  - name: o/my-example-site-a\n  - name: o/example-site-a-fork\n  - name: example-site-q\n"
    out = owner_forms.drop_example_rows(text, ["repos"], 2)
    assert out == "repos:\n  - name: o/my-example-site-a\n"


@pytest.mark.parametrize("tree, rel, key_paths", [
    ("repo-settings", "repo-settings/fleet.yml", [["repos"]]),
    ("agent-guidance", "repos.yml", [["cron_coverage", "fleet"], ["skills_bootstrap", "repos"]]),
])
def test_the_shipped_files_lose_exactly_their_example_rows(tmp_path, tree, rel, key_paths):
    src = KIT / "starter" / tree / rel
    dst = tmp_path / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)
    before = yaml.safe_load(src.read_text(encoding="utf-8"))
    assert owner_forms.drop_example_repos(tmp_path, tree) == [rel] * len(key_paths)
    after = yaml.safe_load(dst.read_text(encoding="utf-8"))
    for key_path in key_paths:
        old, new = before, after
        for key in key_path:
            old, new = old[key], new[key]
        names = [e["name"] if isinstance(e, dict) else e for e in old]
        want = [n for n in names if not n.rsplit("/", 1)[-1].startswith("example-site-")]
        assert len(names) - len(want) == 3
        assert [e["name"] if isinstance(e, dict) else e for e in new] == want


def test_a_tree_without_an_entry_is_left_alone(tmp_path):
    (tmp_path / "f.yml").write_text("repos:\n  - example-site-a\n")
    assert owner_forms.drop_example_repos(tmp_path, "agent-skills") == []
    assert (tmp_path / "f.yml").read_text() == "repos:\n  - example-site-a\n"


def test_a_tree_missing_its_file_fails(tmp_path):
    with pytest.raises(owner_forms.FormError, match="repos.yml is not in the tree"):
        owner_forms.drop_example_repos(tmp_path, "agent-guidance")


def test_invented_stages_nothing_and_an_unknown_form_is_refused(tmp_path):
    (tmp_path / "f.txt").write_text("example-adopter example-adopter-two\n")
    owner_forms.stage(tmp_path, "t", "invented")
    assert (tmp_path / "f.txt").read_text() == "example-adopter example-adopter-two\n"
    with pytest.raises(owner_forms.FormError, match="unknown owner form"):
        owner_forms.stage(tmp_path, "t", "three")


def test_stage_names_the_tree_for_each_form(tmp_path):
    for form, want in (("one", "acme-solo acme-solo"), ("two", "zeta-user alpha-org")):
        d = tmp_path / form
        d.mkdir()
        (d / "f.txt").write_text("example-adopter example-adopter-two\n")
        owner_forms.stage(d, "t", form)
        assert (d / "f.txt").read_text() == want + "\n"


def test_stage_reports_a_substitution_that_refuses(tmp_path):
    (tmp_path / "bad.yml").write_text("a: [example-adopter-two\n")
    with pytest.raises(owner_forms.FormError, match="substitute.py exited"):
        owner_forms.stage(tmp_path, "t", "one")


def test_stage_rebuilds_the_explorer_pages_after_the_zone(tmp_path):
    # Re-pin round 24: explorer/display.json takes the zone and the pages embed
    # it, so a staged skills-evals tree is rebuilt as copy-starter.sh does;
    # stand-in npm and node record their calls (no network).
    import json
    import os
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls.log"
    for tool in ("npm", "node"):
        f = bin_dir / tool
        f.write_text(f'#!/usr/bin/env bash\nprintf "{tool} %s|%s\\n" "$*" "$(cat display.json | tr -d "\\n ")" >> "{log}"\nmkdir -p node_modules\n')
        f.chmod(0o755)
    tree = tmp_path / "tree"
    (tree / "explorer").mkdir(parents=True)
    (tree / "explorer" / "display.json").write_text(json.dumps({"time_zone": "UTC", "issue_repos": ["example-adopter/skills-evals"]}, indent=1) + "\n")
    env = dict(os.environ, PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    owner_forms.stage(tree, "skills-evals", "one", env=env)
    zone = owner_forms.ZONES["one"]
    calls = log.read_text().splitlines()
    assert [c.split("|")[0] for c in calls] == [
        "npm ci --ignore-scripts --no-audit --no-fund --silent", "node build.js", "node build.js --check"]
    # Built from the file as the zone and the names left it.
    assert all(f'"time_zone":"{zone}"' in c and "acme-solo/skills-evals" in c for c in calls), calls
    assert not (tree / "explorer" / "node_modules").exists()
