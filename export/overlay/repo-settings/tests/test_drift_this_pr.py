"""The `drift` job fails only on drift the pull request brings (adoption kit).

scripts/drift_this_pr.py compares the plan of the pull request's fleet.yml
with the plan of the base branch's, and the workflow's "Drift report" step
runs it. These tests run the script on its own, and the step's real script
(taken from the parsed workflow) with `repo_settings.py diff` stubbed and a
real git base commit to fetch. Offline: no gh, no network.

Added by the adoption kit's export (acsi-kit, after its PR #139).
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "drift_this_pr.py"
WORKFLOW = ROOT / ".github" / "workflows" / "repo-settings.yml"

PIN = {"repo": "o/a", "setting": "sha_pinning_required", "status": "drift",
       "current": False, "desired": True}
LABEL = {"repo": "o/a", "setting": "labels[agent-authored]", "status": "drift",
         "current": None, "desired": {"color": "ededed"}}
NOTE = {"repo": "o/b", "setting": "secret_scanning", "status": "advisory",
        "current": None, "desired": True}


def run_script(head, base):
    with tempfile.TemporaryDirectory() as tmp:
        h, b = Path(tmp, "h.json"), Path(tmp, "b.json")
        h.write_text(json.dumps(head))
        b.write_text(json.dumps(base))
        proc = subprocess.run([sys.executable, str(SCRIPT), str(h), str(b)],
                              capture_output=True, text=True, timeout=30)
    return proc.returncode, proc.stdout + proc.stderr


class DriftThisPrScriptTests(unittest.TestCase):
    def test_drift_the_base_brings_too_does_not_fail(self):
        code, out = run_script([PIN], [PIN])
        self.assertEqual(code, 0, out)
        self.assertIn("1 change(s) the base branch's fleet.yml would make too", out)

    def test_drift_of_the_pull_requests_own_fails(self):
        code, out = run_script([PIN, LABEL], [PIN])
        self.assertEqual(code, 1, out)
        self.assertIn("this pull request changes o/a: labels[agent-authored] (drift)", out)

    def test_a_different_desired_value_is_the_pull_requests_own(self):
        code, out = run_script([dict(PIN, desired=False)], [PIN])
        self.assertEqual(code, 1, out)

    def test_an_advisory_of_its_own_is_listed_and_does_not_fail(self):
        code, out = run_script([PIN, NOTE], [PIN])
        self.assertEqual(code, 0, out)
        self.assertIn("o/b: secret_scanning (advisory)", out)

    def test_an_unreadable_file_is_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp, "bad.json")
            bad.write_text("{}")
            proc = subprocess.run([sys.executable, str(SCRIPT), str(bad), str(bad)],
                                  capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 2, proc.stderr)


def drift_step():
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = [s for s in doc["jobs"]["drift"]["steps"] if s.get("name") == "Drift report"]
    assert len(steps) == 1, steps
    return steps[0]


# Stands in for `python`: a `repo_settings.py diff` (the head's engine, or the
# base's copy the step writes) writes the changes the test gives for the head
# (repo-settings/fleet.yml) or the base (any other config) and exits with the
# given code, saying which engine file ran; anything else runs the real
# interpreter.
STUB = """#!/usr/bin/env bash
if [ "$1" = scripts/repo_settings.py ] || [ "${1##*/}" = base-repo_settings.py ]; then
  echo "stub engine $1: $(head -n 1 "$1")" >&2
  cfg="" out=""
  while [ $# -gt 0 ]; do
    case $1 in --config) cfg=$2; shift ;; --changes-json) out=$2; shift ;; esac
    shift
  done
  if [ "$cfg" = repo-settings/fleet.yml ]; then side=HEAD; else side=BASE; fi
  echo "stub diff $side" >&2
  v="${side}_CHANGES"; printf '%s' "${!v}" > "$out"
  v="${side}_RC"; exit "${!v}"
fi
exec "$REAL_PYTHON" "$@"
"""


class DriftStepScriptTests(unittest.TestCase):
    """Runs the "Drift report" step's own script from the parsed workflow."""

    def setUp(self):
        self.step = drift_step()
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(subprocess.run, ["rm", "-rf", str(self.tmp)])
        git = lambda *a, cwd: subprocess.run(  # noqa: E731
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.com",
             "-c", "commit.gpgsign=false", *a],
            cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()
        self.git = git
        self.origin = self.tmp / "origin"
        self.work = self.tmp / "work"
        bin_dir = self.tmp / "bin"
        for d in (self.origin, self.work, bin_dir):
            d.mkdir()
        (bin_dir / "python").write_text(STUB)
        (bin_dir / "python").chmod(0o755)
        self.path = f"{bin_dir}:{os.environ['PATH']}"
        git("init", "-q", "-b", "main", cwd=self.origin)
        (self.work / "scripts").mkdir()
        (self.work / "scripts" / "drift_this_pr.py").write_bytes(SCRIPT.read_bytes())
        (self.work / "scripts" / "repo_settings.py").write_text("# HEAD ENGINE\n")
        git("init", "-q", "-b", "main", cwd=self.work)
        git("remote", "add", "origin", str(self.origin), cwd=self.work)

    def base_commit(self, with_fleet, with_engine=True):
        (self.origin / "README.md").write_text("# r\n")
        if with_engine:
            (self.origin / "scripts").mkdir(exist_ok=True)
            (self.origin / "scripts" / "repo_settings.py").write_text("# BASE ENGINE\n")
        if with_fleet:
            (self.origin / "repo-settings").mkdir(exist_ok=True)
            (self.origin / "repo-settings" / "fleet.yml").write_text("defaults: {}\n")
        self.git("add", "-A", cwd=self.origin)
        self.git("commit", "-q", "-m", "base", cwd=self.origin)
        return self.git("rev-parse", "HEAD", cwd=self.origin)

    def run_step(self, base_sha, head, head_rc, base=(), base_rc=0):
        env = dict(os.environ, PATH=self.path, REAL_PYTHON=sys.executable,
                   OWNER="o", BASE_SHA=base_sha, RUNNER_TEMP=str(self.tmp),
                   HEAD_CHANGES=json.dumps(list(head)), HEAD_RC=str(head_rc),
                   BASE_CHANGES=json.dumps(list(base)), BASE_RC=str(base_rc))
        proc = subprocess.run(["bash", "-e", "-c", self.step["run"]], cwd=self.work, env=env,
                              capture_output=True, text=True, timeout=60)
        return proc.returncode, proc.stdout + proc.stderr

    def test_the_step_reads_the_base_sha_from_env_not_the_script(self):
        self.assertIn("github.event.pull_request.base.sha", self.step["env"]["BASE_SHA"])
        self.assertNotIn("${{", self.step["run"])

    def test_no_drift_passes_without_reading_the_base(self):
        code, out = self.run_step("0" * 40, [], 0)
        self.assertEqual(code, 0, out)
        self.assertNotIn("stub diff BASE", out)

    def test_could_not_plan_the_head_fails(self):
        code, out = self.run_step(self.base_commit(True), [], 2)
        self.assertEqual(code, 2, out)

    def test_the_first_starter_pull_request_passes(self):
        code, out = self.run_step(self.base_commit(False), [PIN], 1)
        self.assertEqual(code, 0, out)
        self.assertIn("the base branch has no repo-settings/fleet.yml yet", out)

    def test_drift_the_base_carries_too_passes(self):
        code, out = self.run_step(self.base_commit(True), [PIN], 1, [PIN], 1)
        self.assertEqual(code, 0, out)
        self.assertIn("stub diff BASE", out)

    def test_the_base_is_planned_with_the_bases_own_engine(self):
        code, out = self.run_step(self.base_commit(True), [PIN], 1, [PIN], 1)
        self.assertEqual(code, 0, out)
        self.assertIn("base-repo_settings.py: # BASE ENGINE", out)
        self.assertIn("stub engine scripts/repo_settings.py: # HEAD ENGINE", out)

    def test_a_base_without_the_engine_fails_on_every_drift(self):
        code, out = self.run_step(self.base_commit(True, with_engine=False), [PIN], 1)
        self.assertEqual(code, 1, out)
        self.assertIn("no scripts/repo_settings.py to plan it with", out)

    def test_drift_of_the_pull_requests_own_fails(self):
        code, out = self.run_step(self.base_commit(True), [PIN, LABEL], 1, [PIN], 1)
        self.assertEqual(code, 1, out)
        self.assertIn("labels[agent-authored]", out)

    def test_a_base_that_cannot_be_planned_fails_on_every_drift(self):
        code, out = self.run_step(self.base_commit(True), [PIN], 1, [], 2)
        self.assertEqual(code, 1, out)
        self.assertIn("could not plan the base branch's fleet.yml", out)

    def test_a_base_that_cannot_be_fetched_fails_on_every_drift(self):
        self.base_commit(True)
        code, out = self.run_step("f" * 40, [PIN], 1)
        self.assertEqual(code, 1, out)
        self.assertIn("could not fetch the base commit", out)


if __name__ == "__main__":
    unittest.main()
