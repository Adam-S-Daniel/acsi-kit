"""resync.py: moving each manifest's pins to its source's head, in place.

No network: every test passes its own ls-remote function.
Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

EXPORT_DIR = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("kit_resync", EXPORT_DIR / "resync.py")
resync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(resync)

OLD, OTHER, NEW, PLATFORM = "a" * 40, "b" * 40, "c" * 40, "d" * 40

ONE = f"""\
# A comment the rewrite must keep.
repo: one
kit_name: one-kit
source: src-one
source_sha: {OLD}   # trailing comment

imports:
  - repo: platform
    sha: {PLATFORM}
    path: x
  - repo: src-one
    sha: '{OLD}'
    path: y
edits:
  - path: z
    old: "pin {OLD}\\n"
    new: "pin {OLD}\\n"
"""

TWO = f"""\
repo: two
source_sha: {OTHER}
"""

PRIVATE = f"""\
repo: agentskills-private
source: secret-src
source_sha: {OTHER}
"""


@pytest.fixture
def manifests(tmp_path):
    d = tmp_path / "manifests"
    d.mkdir()
    (d / "one.yml").write_text(ONE, encoding="utf-8")
    (d / "two.yml").write_text(TWO, encoding="utf-8")
    (d / "agentskills-private.yml").write_text(PRIVATE, encoding="utf-8")
    (d / "_common.yml").write_text("protect: []\n", encoding="utf-8")
    return d


def heads(table):
    calls = []

    def ls_remote(owner, repo):
        calls.append((owner, repo))
        return table[repo]
    return ls_remote, calls


def test_moves_the_source_sha_and_same_repo_imports_and_nothing_else(manifests):
    ls, calls = heads({"src-one": NEW, "two": OTHER})
    got = resync.resync(manifests, "example-owner", ls)
    assert got == [("src-one", OLD, NEW), ("two", OTHER, OTHER)]
    assert sorted(calls) == [("example-owner", "src-one"), ("example-owner", "two")]
    text = (manifests / "one.yml").read_text(encoding="utf-8")
    # Only the two pins moved: comments, quotes, the other repo's import and
    # the same sha inside an edit's text are untouched.
    assert text == ONE.replace(f"source_sha: {OLD}", f"source_sha: {NEW}").replace(f"sha: '{OLD}'", f"sha: '{NEW}'")
    doc = yaml.safe_load(text)
    assert doc["source_sha"] == NEW
    assert [i["sha"] for i in doc["imports"]] == [PLATFORM, NEW]


def test_skips_the_private_manifest_and_never_asks_for_it(manifests):
    ls, calls = heads({"src-one": NEW, "two": NEW})
    resync.resync(manifests, "example-owner", ls)
    assert ("example-owner", "secret-src") not in calls
    assert (manifests / "agentskills-private.yml").read_text(encoding="utf-8") == PRIVATE


def test_unchanged_leaves_the_files_byte_for_byte(manifests):
    ls, _ = heads({"src-one": OLD, "two": OTHER})
    got = resync.resync(manifests, "example-owner", ls)
    assert all(old == new for _, old, new in got)
    assert (manifests / "one.yml").read_text(encoding="utf-8") == ONE
    assert (manifests / "two.yml").read_text(encoding="utf-8") == TWO


def test_a_bad_head_writes_nothing(manifests):
    ls, _ = heads({"src-one": NEW, "two": "not-a-sha"})
    with pytest.raises(resync.ResyncError, match="not a full sha"):
        resync.resync(manifests, "example-owner", ls)
    assert (manifests / "one.yml").read_text(encoding="utf-8") == ONE


def test_refuses_a_bad_owner_an_unsafe_source_and_an_unknown_skip(manifests):
    ls, _ = heads({})
    with pytest.raises(resync.ResyncError, match="not a GitHub owner"):
        resync.resync(manifests, "bad/owner", ls)
    with pytest.raises(resync.ResyncError, match="no manifest for nope"):
        resync.resync(manifests, "example-owner", ls, skip=("nope",))
    (manifests / "two.yml").write_text(f"repo: two\nsource: ../x\nsource_sha: {OTHER}\n", encoding="utf-8")
    with pytest.raises(resync.ResyncError, match="unsafe source repo name"):
        resync.resync(manifests, "example-owner", ls)


def test_refuses_a_short_pinned_sha(manifests):
    (manifests / "two.yml").write_text("repo: two\nsource_sha: abc123\n", encoding="utf-8")
    with pytest.raises(resync.ResyncError, match="not a full sha"):
        resync.resync(manifests, "example-owner", heads({})[0])


def test_main_prints_one_line_per_source_and_writes_the_summary(manifests, tmp_path, capsys):
    ls, _ = heads({"src-one": NEW, "two": OTHER})
    summary = tmp_path / "summary.md"
    rc = resync.main(["--owner", "example-owner", "--manifests", str(manifests), "--summary", str(summary)], ls_remote=ls)
    assert rc == 0
    assert capsys.readouterr().out.splitlines() == [f"src-one: {OLD[:12]} -> {NEW[:12]}", "two: unchanged"]
    md = summary.read_text(encoding="utf-8")
    assert f"https://github.com/example-owner/src-one/compare/{OLD}...{NEW}" in md
    assert "| `two` |" in md and "unchanged" in md


def test_the_real_manifests_all_parse_and_name_a_full_sha():
    for path in sorted((EXPORT_DIR / "manifests").glob("*.yml")):
        if path.name == "_common.yml":
            continue
        key, source, spans = resync.sha_spans(path.read_text(encoding="utf-8"), path.name)
        assert spans and all(resync.SHA.fullmatch(s) for _, _, s in spans), path.name


# ── The workflow: a failed re-sync is reported in one issue ─────────────────

WORKFLOW = EXPORT_DIR.parent / ".github" / "workflows" / "resync.yml"
ISSUE_TITLE = "Re-sync from sources is failing"


def _job():
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return doc, doc["jobs"]["resync"]


def test_the_workflow_reads_at_workflow_level_and_the_job_adds_issues_write_and_pull_request_read_only():
    doc, job = _job()
    assert doc["permissions"] == {"contents": "read"}
    assert job["permissions"] == {"contents": "read", "issues": "write", "pull-requests": "read"}


def test_no_run_block_interpolates_an_expression():
    _, job = _job()
    for step in job["steps"]:
        assert "${{" not in step.get("run", ""), step.get("name")


def _step(job, name):
    return next(s for s in job["steps"] if s.get("name") == name)


def test_a_failure_opens_or_updates_one_issue_and_a_clean_success_closes_it():
    _, job = _job()
    report = _step(job, "Open or update the failure issue")
    close = _step(job, "Close the failure issue")
    assert job["steps"][-2:] == [report, close]
    assert report["if"] == "failure()"
    assert close["if"] == "success() && steps.holdback.outputs.held_back == ''"
    for step in (report, close):
        assert "uses" not in step
        assert step["env"]["ISSUE_TITLE"] == ISSUE_TITLE
        assert step["env"]["GH_TOKEN"] == "${{ github.token }}"
        assert step["env"]["RUN_URL"] == (
            "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}")
        assert "select(.title == env.ISSUE_TITLE)" in step["run"]
    run = report["run"]
    assert "gh issue create" in run and "gh issue edit" in run and "gh issue comment" in run
    # The body opens with the TLDR heading, and the label is best effort.
    assert run.index("printf '## TLDR") < run.index("printf 'The daily")
    assert "--add-label agent-authored > /dev/null \\\n" in run and "|| echo \"::warning::" in run
    # It names the failed step from the step outcomes, never the log.
    named = {"resync", "holdback", "push", "fire"}
    assert {k.removeprefix("OUTCOME_").lower() for k in report["env"] if k.startswith("OUTCOME_")} == named
    assert named <= {s.get("id") for s in job["steps"]}
    assert "gh run view" not in run and "--log" not in run
    assert "gh issue close" in close["run"]


def test_one_step_regenerates_with_the_holdback_and_keeps_the_denylist_guard():
    _, job = _job()
    names = [s.get("name") for s in job["steps"]]
    assert "Export tests" not in names and "Regenerate starter/" not in names
    step = _step(job, "Regenerate starter/, holding back a source that breaks it")
    assert step["id"] == "holdback" and step["if"] == "steps.resync.outputs.changed == 'true'"
    assert step["env"]["PRIVACY_DENYLIST"] == "${{ secrets.PRIVACY_DENYLIST }}"
    run = step["run"]
    assert 'PRIVACY_DENYLIST//[[:space:]]/' in run and "exit 1" in run
    # Old pins are fetched too, and the script is the only thing that runs the tests.
    assert "export/fetch_sources.py" in run and "--also-pins-at HEAD" in run
    assert "export/resync_holdback.py" in run and "--tails" in run
    assert "pytest" not in run and "npm" not in run
    # The tails file is never printed or uploaded.
    assert "cat " not in run and not any("upload-artifact" in str(s.get("uses", "")) for s in job["steps"])


def test_all_held_means_no_pull_request():
    _, job = _job()
    for name in ("Check for the App",):
        assert "steps.holdback.outputs.all_held != 'true'" in _step(job, name)["if"]
    for name in ("Mint the App token", "Push resync/auto and open or update the pull request"):
        assert _step(job, name)["if"].startswith("steps.app.outputs.configured")


def test_a_held_back_source_opens_the_issue_without_failing_the_job():
    _, job = _job()
    held = _step(job, "Open or update the held-back issue")
    assert held["if"] == "success() && steps.holdback.outputs.held_back != ''"
    assert held["env"]["ISSUE_TITLE"] == ISSUE_TITLE
    assert held["env"]["HELD_BACK"] == "${{ steps.holdback.outputs.held_back }}"
    assert held["env"]["RUN_URL"].endswith("/actions/runs/${{ github.run_id }}")
    run = held["run"]
    assert "gh issue create" in run and "gh issue edit" in run and "gh issue comment" in run
    assert "$HELD_BACK" in run and "$RUN_URL" in run
    # Never a log: no run view, and the tails file is not read.
    assert "gh run view" not in run and "--log" not in run and "holdback-tails" not in run
    # It sits before the failure steps, after the pull request is pushed.
    order = [s.get("name") for s in job["steps"]]
    assert order.index("Push resync/auto and open or update the pull request") < order.index(held["name"]) < order.index("Open or update the failure issue")


def test_a_held_back_source_fires_the_fix_routine_at_most_once_a_day():
    _, job = _job()
    fire = _step(job, "Fire the fix routine")
    assert fire["id"] == "fire"
    assert fire["if"] == "success() && steps.holdback.outputs.held_back != ''"
    env = fire["env"]
    # One place each, no default: a variable and a secret.
    assert env["FIRE_URL"] == "${{ vars.RESYNC_FIXER_FIRE_URL }}"
    assert env["FIRE_BEARER"] == "${{ secrets.RESYNC_FIXER_FIRE_BEARER }}"
    assert env["ISSUE_NUMBER"] == "${{ steps.heldissue.outputs.number }}"
    run = fire["run"]
    assert "variable RESYNC_FIXER_FIRE_URL" in run and "secret RESYNC_FIXER_FIRE_BEARER" in run
    # Skips while a fix pull request is open, and after today's marker.
    assert 'startswith("resync-fix/")' in run and "isCrossRepository | not" in run
    assert 'select(.user.login == "github-actions[bot]")' in run
    assert "resync-fixer-fired $(date -u +%F)" in run and "grep -qF --" in run
    # The bearer goes on stdin, the request from a file; neither is printed.
    assert "--config -" in run and '--data-binary "@$request"' in run
    assert 'echo "$FIRE_BEARER' not in run and 'cat "$request' not in run
    assert "holdback-tails.txt" in run
    order = [s.get("name") for s in job["steps"]]
    assert order.index("Open or update the held-back issue") < order.index("Fire the fix routine") < order.index("Open or update the failure issue")
    assert _step(job, "Open or update the held-back issue")["id"] == "heldissue"
    assert "OUTCOME_FIRE" in _step(job, "Open or update the failure issue")["env"]


def test_the_fix_routine_guide_names_the_branch_prefix_the_workflow_watches():
    guide = (EXPORT_DIR / "FIX-ROUTINE.md").read_text(encoding="utf-8")
    assert "resync-fix/" in guide


def test_runs_queue_so_two_cannot_both_fire_the_routine():
    doc, _ = _job()
    assert doc["concurrency"] == {"group": "resync", "cancel-in-progress": False}


# ── The fix routine's pull request is opened by a workflow ──────────────────

FIX_WORKFLOW = EXPORT_DIR.parent / ".github" / "workflows" / "resync-fix-pr.yml"
ACTIONS_LOCK = EXPORT_DIR.parent / ".github" / "workflows" / "actions.lock"


def _fix_job():
    doc = yaml.safe_load(FIX_WORKFLOW.read_text(encoding="utf-8"))
    return doc, doc["jobs"]["open-pr"]


def test_the_fix_pr_workflow_runs_only_on_resync_fix_pushes_with_least_privilege():
    doc, job = _fix_job()
    on = doc.get("on", doc.get(True))
    assert on == {"push": {"branches": ["resync-fix/**"]}}
    assert doc["permissions"] == {"contents": "read"}
    assert job["permissions"] == {"contents": "read", "issues": "write"}
    assert len(doc["jobs"]) == 1
    for step in job["steps"]:
        assert "${{" not in step.get("run", ""), step.get("name")


def test_the_fix_pr_workflow_opens_the_pull_request_with_the_app_token_after_checking_for_one():
    _, job = _fix_job()
    mint = _step(job, "Mint the App token")
    assert mint["uses"] == "actions/create-github-app-token@v3.2.0"
    assert mint["with"]["permission-contents"] == "write"
    assert mint["with"]["permission-pull-requests"] == "write"
    step = _step(job, "Open the pull request and link it on the issue")
    assert step["env"]["GH_TOKEN"] == "${{ steps.token.outputs.token }}"
    assert step["env"]["ISSUE_TOKEN"] == "${{ github.token }}"
    run = step["run"]
    assert "^resync-fix/[0-9A-Za-z._/-]+$" in run
    assert run.index("gh pr list --repo") < run.index("gh pr create")
    assert "--state open" in run and "--body-file" in run and "## TLDR" in run
    assert 'GH_TOKEN="$ISSUE_TOKEN" gh issue comment' in run
    assert "Fix routine pull request:" in run
    # The commit message is never printed.
    assert 'echo "$message' not in run and 'printf "%s" "$message' not in run
    assert "agent-authored" in run


def test_the_actions_lock_lists_the_fix_pr_workflow():
    lock = yaml.safe_load(ACTIONS_LOCK.read_text(encoding="utf-8"))
    assert lock["workflows"][".github/workflows/resync-fix-pr.yml"] == [
        "actions/create-github-app-token@v3.2.0"]
    keys = list(lock["workflows"])
    assert keys == sorted(keys)


def test_a_run_with_nothing_to_move_closes_a_stale_resync_pull_request():
    _, job = _job()
    names = [s.get("name") for s in job["steps"]]
    close = _step(job, "Close a stale re-sync pull request")
    assert close["if"] == "steps.app.outputs.configured == 'true' && steps.resync.outputs.changed == 'false'"
    assert close["env"]["GH_TOKEN"] == "${{ steps.token.outputs.token }}"
    assert "gh pr close" in close["run"] and "isCrossRepository" in close["run"]
    assert "could not list open pull requests" in close["run"] and "exit 1" in close["run"]
    assert "<sub>🤖 Written by the daily re-sync on behalf of @$OWNER</sub>" in close["run"]
    assert close["env"]["OWNER"] == "${{ github.repository_owner }}"
    push = "Push resync/auto and open or update the pull request"
    assert names.index(push) < names.index(close["name"])
    assert "steps.resync.outputs.changed == 'true'" in _step(job, push)["if"]
    # The App steps also run when nothing changed.
    assert _step(job, "Check for the App")["if"] == "steps.holdback.outputs.all_held != 'true'"


def test_the_fix_routine_leaves_the_pull_request_to_the_workflow():
    guide = (EXPORT_DIR / "FIX-ROUTINE.md").read_text(encoding="utf-8")
    assert "resync-fix-pr.yml" in guide
    assert "Do not open a pull request" in guide
