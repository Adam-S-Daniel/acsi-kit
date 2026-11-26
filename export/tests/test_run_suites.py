"""run_suites.py's known-failure matching, and the list it is given.

A known failure is excused only by its exact id, and only when the listed
ids account for the whole failure; these tests hold both halves, and hold
starter/known-failures.txt to the format and to trees that exist.

Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
EXPORT_DIR = HERE.parent
KIT = EXPORT_DIR.parent

_spec = importlib.util.spec_from_file_location("kit_run_suites", EXPORT_DIR / "run_suites.py")
run_suites = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("kit_run_suites", run_suites)
_spec.loader.exec_module(run_suites)

PYTEST_OUT = """\
FAILED test/a.py::T::test_one - AssertionError: 1 != 2
SUBFAILED(case="'x y'") test/a.py::T::test_two - AssertionError
ERROR test/b.py::test_setup
SKIPPED [1] test/c.py:3: needs bwrap
====== 2 failed, 10 passed, 1 skipped, 1 error in 3.21s ======
"""
GROUP_OUT = """\
      codex_cloud        - passed,   - failed, exit 1, 63s
      FAILED GROUPS: codex_cloud
      Results: 2212 passed, 1 failed
"""
UNITTEST_GROUP_OUT = """\
test_ok (test_m.T.test_ok) ... ok
======================================================================
FAIL: test_a (test_m.T.test_a) (kind='unreadable')
----------------------------------------------------------------------
AssertionError: 1 != 0
======================================================================
FAIL: test_b (test_m.T.test_b)
----------------------------------------------------------------------
AssertionError
----------------------------------------------------------------------
Ran 90 tests in 45.213s

FAILED (failures=2, skipped=1)
  Groups (TEST_JOBS=4):
  codex_cloud        - passed,   - failed, exit 1, 45s (+1 failed: exited 1 without reporting a failed assertion)
  FAILED GROUPS: codex_cloud
  Results: 0 passed, 1 failed
"""
UNITTEST_IDS = {"FAIL: test_m.T.test_a (kind='unreadable')", "FAIL: test_m.T.test_b"}
IDS = {"FAILED test/a.py::T::test_one", "SUBFAILED(case=\"'x y'\") test/a.py::T::test_two", "ERROR test/b.py::test_setup"}


def test_pytest_ids_drop_the_reason_and_keep_subtest_parameters():
    ids, problem = run_suites.failure_ids(PYTEST_OUT)
    assert ids == IDS
    assert problem is None


def test_group_ids_come_from_the_failed_groups_line():
    assert run_suites.failure_ids(GROUP_OUT) == ({"group:codex_cloud"}, None)


def test_an_exit_only_group_is_named_by_its_unittest_failures():
    assert run_suites.failure_ids(UNITTEST_GROUP_OUT) == (UNITTEST_IDS, None)
    ok, lines = run_suites.judge(UNITTEST_GROUP_OUT, {i: 1 for i in UNITTEST_IDS})
    assert ok, lines


def test_a_new_unittest_failure_in_an_excused_group_is_not_hidden():
    ok, lines = run_suites.judge(UNITTEST_GROUP_OUT, {"FAIL: test_m.T.test_a (kind='unreadable')": 1})
    assert not ok
    assert "NEW FAILURE (not in the known list): FAIL: test_m.T.test_b" in lines


def test_a_group_with_a_failed_assertion_is_still_named_as_a_group():
    out = UNITTEST_GROUP_OUT.replace(
        "  codex_cloud        - passed,   - failed, exit 1, 45s (+1 failed: exited 1 without reporting a failed assertion)",
        "  codex_cloud        3 passed,   1 failed, exit 1, 45s").replace("  Results: 0 passed", "  FAIL: a shell check\n  Results: 3 passed")
    ok, lines = run_suites.judge(out, {i: 1 for i in UNITTEST_IDS})
    assert not ok
    assert "NEW FAILURE (not in the known list): group:codex_cloud" in lines


def test_unittest_headers_must_account_for_its_count():
    out = UNITTEST_GROUP_OUT.replace("FAILED (failures=2, skipped=1)", "FAILED (failures=2, errors=1, skipped=1)")
    ok, lines = run_suites.judge(out, {i: 1 for i in UNITTEST_IDS})
    assert not ok
    assert any("unittest reports 3 failures and errors, but 2" in line for line in lines)


def test_all_known_failures_are_excused_and_named():
    ok, lines = run_suites.judge(PYTEST_OUT, {i: 1 for i in IDS})
    assert ok
    assert sum(line.startswith("known failure (excused): ") for line in lines) == 3


def test_one_new_failure_is_not_excused():
    known = {i: 1 for i in IDS if "test_one" not in i}
    ok, lines = run_suites.judge(PYTEST_OUT, known)
    assert not ok
    assert "NEW FAILURE (not in the known list): FAILED test/a.py::T::test_one" in lines


def test_a_failure_that_names_nothing_is_never_excused():
    ok, lines = run_suites.judge("Traceback (most recent call last):\nboom\n", {"group:codex_cloud": 1})
    assert not ok
    assert any(line.startswith("NOT EXCUSED: ") for line in lines)


def test_ids_that_do_not_account_for_the_pytest_count_are_not_excused():
    # A failure line the parser cannot read (here, cut from the log) must not
    # let the rest pass as the whole failure.
    out = PYTEST_OUT.replace("ERROR test/b.py::test_setup\n", "")
    ok, lines = run_suites.judge(out, {i: 1 for i in IDS})
    assert not ok
    assert any("pytest reports 3 failed or errored, but 2" in line for line in lines)


def test_a_listed_id_that_did_not_fail_is_reported_not_fatal():
    ok, lines = run_suites.judge(GROUP_OUT, {"group:codex_cloud": 1, "group:sync": 2})
    assert ok
    assert "listed as known but did not fail: group:sync" in lines


def test_load_known_refuses_a_duplicate_and_a_bare_line(tmp_path):
    p = tmp_path / "k.txt"
    p.write_text("# c\nt FAILED x::y\nt FAILED x::y\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="listed twice"):
        run_suites.load_known(p)
    p.write_text("lonely\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="want '<tree> <failure id>'"):
        run_suites.load_known(p)


def test_the_kits_known_failures_name_real_trees_with_well_formed_ids():
    known = run_suites.load_known(KIT / "starter" / "known-failures.txt")
    trees = {m["kit_name"] for m in run_suites.export.load_manifests().values()}
    assert set(known) <= trees
    for tree, ids in known.items():
        for i in ids:
            assert (i.startswith("group:") or run_suites.PYTEST_ID.fullmatch(i)
                    or re.fullmatch(r"(?:FAIL|ERROR): [\w.]+(?: \(.*\))?", i)), (tree, i)


def test_a_failed_setup_probe_stops_the_setup_even_when_a_command_follows_it(tmp_path, monkeypatch):
    # agentskills.yml's setup was `python3 -I -c 'import ... bashlex ...'; if
    # [ root ]; then ...; fi`: without errexit its status was the `if`'s, so a
    # missing bashlex surfaced as pytest exit 3, not as the suite's needs.
    (tmp_path / "t").mkdir()
    monkeypatch.setattr(run_suites.export, "STARTER", tmp_path)
    suite = {"setup": "false; true", "command": "echo SUITE RAN", "needs": "the probe's package"}
    ok, summary, log, _ = run_suites.run_one("t", suite, keep=False)
    assert not ok
    assert summary == "setup exited 1 (needs: the probe's package)"
    assert "SUITE RAN" not in log


def _fake_tree(tmp_path, monkeypatch, name):
    (tmp_path / name).mkdir()
    (tmp_path / name / "f.txt").write_text("x")
    monkeypatch.setattr(run_suites.export, "STARTER", tmp_path)


# Setup "installs" a marker module into the active interpreter's site-packages,
# the way pip would, without the network: what matters is which interpreter's
# site-packages the write lands in.
INSTALL = (
    'python3 -c \'import pathlib, site, sys; '
    'p = pathlib.Path(site.getsitepackages()[0]) / "marker_%s.py"; '
    'p.write_text("V = %s\\n"); print("wrote", p)\''
)
TRY_IMPORT = (
    'python3 -c \'import importlib.util as u; '
    'print("SEES", [n for n in ("marker_a", "marker_b") if u.find_spec(n)])\''
)


def test_each_installing_suite_gets_its_own_environment(tmp_path, monkeypatch):
    _fake_tree(tmp_path, monkeypatch, "a")
    (tmp_path / "b").mkdir()
    monkeypatch.setattr(run_suites.export, "STARTER", tmp_path)
    ok_a, _, log_a, _ = run_suites.run_one(
        "a", {"venv": True, "setup": INSTALL % ("a", 1), "command": TRY_IMPORT}, keep=False)
    ok_b, _, log_b, _ = run_suites.run_one(
        "b", {"venv": True, "setup": INSTALL % ("b", 2), "command": TRY_IMPORT}, keep=False)
    assert ok_a and ok_b
    # Each sees only its own marker, and the install landed in a venv.
    assert "SEES ['marker_a']" in log_a and "marker_b" not in log_a.split("SEES")[1]
    assert "SEES ['marker_b']" in log_b
    assert "kit-suite-a-" in log_a and "/venv/" in log_a
    # The base interpreter sees neither.
    import importlib.util
    assert importlib.util.find_spec("marker_a") is None
    assert importlib.util.find_spec("marker_b") is None


def test_the_venv_is_deleted_with_the_copy(tmp_path, monkeypatch):
    _fake_tree(tmp_path, monkeypatch, "a")
    ok, _, log, _ = run_suites.run_one("a", {"venv": True, "command": "echo $VIRTUAL_ENV"}, keep=False)
    assert ok
    venv = [l for l in log.splitlines() if l.endswith("/venv")][0]
    assert not Path(venv).exists()


def test_a_suite_that_installs_nothing_gets_no_venv(tmp_path, monkeypatch):
    _fake_tree(tmp_path, monkeypatch, "a")
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    ok, _, log, _ = run_suites.run_one(
        "a", {"command": 'echo "VENV=[${VIRTUAL_ENV:-}]"; ls ..'}, keep=False)
    assert ok
    assert "VENV=[]" in log
    assert "venv" not in log.split("VENV=[]")[1]


def test_only_skills_evals_declares_a_venv():
    manifests = run_suites.export.load_manifests()
    with_venv = sorted(m["kit_name"] for m in manifests.values() if (m.get("suite") or {}).get("venv"))
    assert with_venv == ["skills-evals"]


# ---- --owners: the copy gets the names and edits of an adopter's tree

def _named_tree(tmp_path, monkeypatch, name="t"):
    d = tmp_path / name
    d.mkdir()
    (d / "f.txt").write_text("example-adopter and example-adopter-two\n")
    monkeypatch.setattr(run_suites.export, "STARTER", tmp_path)
    return d


@pytest.mark.parametrize("form, want", [
    ("invented", "example-adopter and example-adopter-two"),
    ("one", "acme-solo and acme-solo"),
    ("two", "zeta-user and alpha-org"),
])
def test_each_owner_form_names_the_copy_and_its_commit(tmp_path, monkeypatch, form, want):
    _named_tree(tmp_path, monkeypatch)
    # The suite reads the file and the history: the committed tree is the
    # staged one, so the substitution ran before the commit.
    suite = {"git_init": True, "command": "cat f.txt; git show HEAD:f.txt"}
    ok, _, log, _ = run_suites.run_one("t", suite, keep=False, owners=form)
    assert ok
    assert log.count(want + "\n") == 2, log


def test_the_default_form_is_the_invented_one(tmp_path, monkeypatch):
    _named_tree(tmp_path, monkeypatch)
    ok, _, log, _ = run_suites.run_one("t", {"command": "cat f.txt"}, keep=False)
    assert ok and "example-adopter and example-adopter-two" in log
    assert run_suites.run_one.__defaults__[-1] == "invented"


def test_a_form_that_cannot_be_staged_fails_without_running_the_suite(tmp_path, monkeypatch):
    d = _named_tree(tmp_path, monkeypatch)
    (d / "broken.yml").write_text("a: [example-adopter-two\n")
    ok, summary, log, _ = run_suites.run_one("t", {"command": "echo SUITE RAN"}, keep=False, owners="one")
    assert not ok
    assert "one owner form could not be staged" in summary and "substitute.py exited" in summary
    assert "SUITE RAN" not in log


def test_the_second_form_drops_the_example_repos_of_the_trees_that_name_them(tmp_path, monkeypatch):
    d = _named_tree(tmp_path, monkeypatch, "repo-settings")
    (d / "repo-settings").mkdir()
    (d / "repo-settings" / "fleet.yml").write_text(
        "repos:\n  - name: example-adopter/real\n    manage: [\"all\"]\n"
        "  - name: example-adopter/example-site-platform\n    manage: [\"labels\"]\n")
    # three rows are expected, so a tree with one fails loudly
    ok, summary, _, _ = run_suites.run_one("repo-settings", {"command": "true"}, keep=False, owners="two")
    assert not ok and "expected 3" in summary
    ok, _, _, _ = run_suites.run_one("repo-settings", {"command": "true"}, keep=False, owners="one")
    assert ok   # the first form leaves the rows in


def test_main_passes_the_form_through_and_names_it(tmp_path, monkeypatch, capsys):
    seen = []

    def fake_run_one(kit_name, suite, keep, known=None, owners="invented"):
        seen.append((kit_name, owners, known))
        return True, "fine (exit 0)", "", []

    monkeypatch.setattr(run_suites, "run_one", fake_run_one)
    monkeypatch.setattr(run_suites.export, "load_manifests",
                        lambda: {"t": {"kit_name": "t", "suite": {"command": "true"}}})
    assert run_suites.main(["--kit-name", "t", "--owners", "one"]) == 0
    assert run_suites.main(["--kit-name", "t"]) == 0
    assert [s[:2] for s in seen] == [("t", "one"), ("t", "invented")]
    out = capsys.readouterr().out.splitlines()
    assert out == ["PASS t (one): fine (exit 0)", "PASS t: fine (exit 0)"]


def test_an_unknown_form_is_refused_by_the_parser(capsys):
    with pytest.raises(SystemExit) as e:
        run_suites.main(["--owners", "three"])
    assert e.value.code == 2


def test_known_failures_still_excuse_a_failure_in_a_substituted_form(tmp_path, monkeypatch):
    _named_tree(tmp_path, monkeypatch)
    known = {"FAIL: test_m.T.test_a": 1}
    suite = {"command": ("printf 'FAIL: test_a (test_m.T.test_a)\\n----\\nFAILED (failures=1)\\n'; "
                         "grep -q acme-solo f.txt; exit 1")}
    ok, summary, log, notes = run_suites.run_one("t", suite, keep=False, known=known, owners="one")
    assert ok and "1 known failure(s) excused" in summary
    assert notes == ["known failure (excused): FAIL: test_m.T.test_a"]


# ---- starter/run-all-tests.sh: which runs it starts, and how it counts them

TREES = ("agent-guidance", "repo-settings", "agent-skills", "agent-skills-private", "wsl-automation")


def _run_all(tmp_path, fail_key="", forms=None):
    """starter/run-all-tests.sh in a copy of the kit's layout, with a stand-in
    python3 that passes every run but `fail_key` ("<tree>.<form>") and records
    each run it was asked for."""
    (tmp_path / "starter").mkdir()
    shutil.copy(KIT / "starter" / "run-all-tests.sh", tmp_path / "starter" / "run-all-tests.sh")
    manifests = tmp_path / "export" / "manifests"
    manifests.mkdir(parents=True)
    for tree in TREES + ("skills-evals",):
        (manifests / f"{tree}.yml").write_text(f"kit_name: {tree}\n")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake = fake_bin / "python3"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        "tree= form=\n"
        "while [ $# -gt 0 ]; do case $1 in --kit-name) tree=$2; shift;; --owners) form=$2; shift;; esac; shift; done\n"
        'echo "$tree.$form" >> "$RUN_ALL_SEEN"\n'
        'if [ "$tree.$form" = "$RUN_ALL_FAIL" ]; then echo "FAIL $tree ($form): 1 failed"; exit 1; fi\n'
        'echo "PASS $tree ($form): 1 passed"\n')
    fake.chmod(0o755)
    seen = tmp_path / "seen"
    seen.write_text("")
    env = dict(os.environ, PATH=f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
               RUN_ALL_SEEN=str(seen), RUN_ALL_FAIL=fail_key, RUN_ALL_JOBS="3")
    env.pop("RUN_ALL_FORMS", None)
    if forms is not None:
        env["RUN_ALL_FORMS"] = forms
    p = subprocess.run(["bash", str(tmp_path / "starter" / "run-all-tests.sh")],
                       capture_output=True, text=True, env=env)
    return p, sorted(seen.read_text().split())


def test_run_all_starts_each_base_tree_in_three_forms_and_skills_evals_once(tmp_path):
    p, seen = _run_all(tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    want = sorted([f"{t}.{f}" for t in TREES for f in ("invented", "one", "two")] + ["skills-evals.invented"])
    assert seen == want
    assert p.stdout.splitlines()[-1].startswith("runs: 16 passed, 0 failed, 16 total")


def test_run_all_fails_when_one_form_of_one_tree_fails(tmp_path):
    p, _ = _run_all(tmp_path, fail_key="repo-settings.two")
    assert p.returncode == 1
    assert "FAIL repo-settings (two) (exit 1):" in p.stdout
    assert p.stdout.splitlines()[-1].startswith("runs: 15 passed, 1 failed, 16 total")


@pytest.mark.parametrize("forms, want", [
    ("one", [f"{t}.one" for t in TREES]),
    ("invented", [f"{t}.invented" for t in TREES] + ["skills-evals.invented"]),
    ("two one", [f"{t}.{f}" for t in TREES for f in ("one", "two")]),
])
def test_run_all_forms_limits_the_runs_and_skills_evals_goes_with_invented(tmp_path, forms, want):
    p, seen = _run_all(tmp_path, forms=forms)
    assert p.returncode == 0, p.stdout + p.stderr
    assert seen == sorted(want)
    assert p.stdout.splitlines()[-1].startswith(f"runs: {len(want)} passed, 0 failed, {len(want)} total")


@pytest.mark.parametrize("forms", ["three", "one three", " "])
def test_run_all_refuses_a_form_it_does_not_know(tmp_path, forms):
    p, seen = _run_all(tmp_path, forms=forms)
    assert p.returncode == 2 and seen == []
    assert "RUN_ALL_FORMS" in p.stderr


def test_ci_runs_one_leg_per_owner_form_behind_one_required_job():
    import yaml
    jobs = yaml.safe_load((KIT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))["jobs"]
    legs, gate = jobs["suites"], jobs["starter-suites"]
    # Every form run_suites.py knows has a leg, and a leg runs its form alone.
    assert sorted(legs["strategy"]["matrix"]["form"]) == sorted(run_suites.owner_forms.CHOICES)
    assert legs["strategy"]["fail-fast"] is False
    runs = [s for s in legs["steps"] if "starter/run-all-tests.sh" in str(s.get("run", ""))]
    assert len(runs) == 1 and runs[0]["env"]["RUN_ALL_FORMS"] == "${{ matrix.form }}"
    # The required context waits for the legs and cannot be skipped.
    assert gate["name"] == "starter-suites" and gate["needs"] == ["suites"] and gate["if"] == "always()"
    assert "needs.suites.result" in str(gate["steps"][0]["env"])
    assert "!= success" in gate["steps"][0]["run"] and "exit 1" in gate["steps"][0]["run"]
    # A required check that can fire twice on one head takes no concurrency group.
    assert "concurrency" not in legs and "concurrency" not in gate
