"""resync.py: moving each manifest's pins to its source's head, in place.

No network: every test passes its own ls-remote function.
Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
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
    named = {"resync", "token", "holdback", "push", "closestale", "fire"}
    assert {k.removeprefix("OUTCOME_").lower() for k in report["env"] if k.startswith("OUTCOME_")} == named
    assert named <= {s.get("id") for s in job["steps"]}
    assert "gh run view" not in run and "--log" not in run
    assert "gh issue close" in close["run"]


def test_the_pages_to_review_step_runs_after_holdback_and_before_the_summary_is_read_and_never_blocks():
    _, job = _job()
    names = [s.get("name") for s in job["steps"]]
    step = _step(job, "List the pages a changed source makes stale")
    holdback = names.index("Regenerate starter/, holding back a source that breaks it")
    # After hold-back settles the pins; before the summary is shown and the
    # pull request body (built in the push step) reads the summary file.
    assert holdback < names.index(step["name"]) < names.index("Show the summary")
    assert names.index(step["name"]) < names.index("Push resync/auto and open or update the pull request")
    assert step["if"] == "steps.resync.outputs.changed == 'true'"
    run = step["run"]
    assert 'python3 export/doc_review.py --base HEAD --summary "$RUNNER_TEMP/resync-summary.md"' in run
    assert '|| echo "::warning::' in run
    assert "continue-on-error" not in step


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
    assert '--held-heads "$RUNNER_TEMP/held-heads.json"' in run
    assert "pytest" not in run and "npm" not in run
    # The tails file is never printed or uploaded.
    assert "cat " not in run and not any("upload-artifact" in str(s.get("uses", "")) for s in job["steps"])


def test_all_held_means_no_pull_request_but_the_app_is_still_wanted():
    _, job = _job()
    # The App closes a stale fix pull request even when everything is held back.
    assert "if" not in _step(job, "Check for the App")
    assert _step(job, "Mint the App token")["if"] == "steps.app.outputs.configured == 'true'"
    push = _step(job, "Push resync/auto and open or update the pull request")["if"]
    assert push.startswith("steps.app.outputs.configured == 'true'")
    assert "steps.holdback.outputs.all_held != 'true'" in push and "steps.resync.outputs.changed == 'true'" in push


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
    # Today's marker is checked before any pull request is listed or closed.
    assert 'select(.user.login == "github-actions[bot]")' in run
    assert "resync-fixer-fired $(date -u +%F)" in run and "grep -qF --" in run
    assert run.index("grep -qF --") < run.index("gh pr list") < run.index("gh pr close")
    # Only this repository's own fix branches count; a stale one is closed with
    # the App's token, and the job's permissions stay read-only for pull requests.
    assert 'startswith("resync-fix/")' in run and "isCrossRepository | not" in run
    assert env["APP_TOKEN"] == "${{ steps.token.outputs.token }}"
    assert 'GH_TOKEN="$APP_TOKEN" gh pr close' in run and "python3 export/resync_stale_fix.py" in run
    assert "<sub>🤖 Written by the daily re-sync on behalf of @%s</sub>" in run
    assert job["permissions"]["pull-requests"] == "read"
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


PUSHED_WORKFLOW = EXPORT_DIR.parent / ".github" / "workflows" / "resync-fix-pushed.yml"


def _on(doc):
    return doc.get("on", doc.get(True))


def _fix_job():
    doc = yaml.safe_load(FIX_WORKFLOW.read_text(encoding="utf-8"))
    return doc, doc["jobs"]["open-pr"]


def test_the_pushed_workflow_triggers_only_on_resync_fix_pushes_and_holds_nothing():
    text = PUSHED_WORKFLOW.read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    assert _on(doc) == {"push": {"branches": ["resync-fix/**"]}}
    assert doc["permissions"] in ({}, {"contents": "read"})
    assert len(doc["jobs"]) == 1
    (job,) = doc["jobs"].values()
    assert job["if"] == "${{ !github.event.deleted }}"
    assert "secrets." not in text
    assert all("uses" not in s for s in job["steps"]) and len(job["steps"]) == 1
    assert "run" in job["steps"][0] and "${{" not in job["steps"][0]["run"]


def test_the_fix_pr_workflow_runs_only_after_the_pushed_workflow_with_least_privilege():
    pushed = yaml.safe_load(PUSHED_WORKFLOW.read_text(encoding="utf-8"))
    doc, job = _fix_job()
    assert _on(doc) == {"workflow_run": {"workflows": [pushed["name"]], "types": ["completed"]}}
    assert pushed["name"] == "Re-sync fix branch pushed"
    assert doc["permissions"] == {"contents": "read"}
    assert job["permissions"] == {"contents": "read", "issues": "write"}
    assert len(doc["jobs"]) == 1
    cond = " ".join(job["if"].split())
    assert "github.event.workflow_run.conclusion == 'success'" in cond
    assert "github.event.workflow_run.event == 'push'" in cond
    assert "github.event.workflow_run.head_repository.full_name == github.repository" in cond
    assert job["concurrency"] == {
        "group": "resync-fix-pr-${{ github.event.workflow_run.head_branch }}",
        "cancel-in-progress": False}
    for step in job["steps"]:
        assert "${{" not in step.get("run", ""), step.get("name")


def test_the_fix_pr_workflow_opens_the_pull_request_with_the_app_token_after_checking_for_one():
    _, job = _fix_job()
    mint = _step(job, "Mint the App token")
    # Any exact release tag: Dependabot bumps it, and a hard-coded version
    # here failed every such bump's CI.
    assert re.fullmatch(r"actions/create-github-app-token@v\d+\.\d+\.\d+", mint["uses"])
    assert mint["with"]["permission-contents"] == "read"
    assert mint["with"]["permission-pull-requests"] == "write"
    step = _step(job, "Open the pull request and link it on the issue")
    assert step["env"]["GH_TOKEN"] == "${{ steps.token.outputs.token }}"
    assert step["env"]["ISSUE_TOKEN"] == "${{ github.token }}"
    assert step["env"]["BRANCH"] == "${{ github.event.workflow_run.head_branch }}"
    assert step["env"]["HEAD_SHA"] == "${{ github.event.workflow_run.head_sha }}"
    run = step["run"]
    assert "^resync-fix/[0-9A-Za-z._/-]+$" in run
    assert run.index("gh pr list --repo") < run.index("gh pr create")
    assert "--state open" in run and "--body-file" in run and "## TLDR" in run
    assert 'GH_TOKEN="$ISSUE_TOKEN" gh issue comment' in run
    assert "Fix routine pull request:" in run
    # The commit message is never printed.
    assert 'echo "$message' not in run and 'printf "%s" "$message' not in run
    assert "agent-authored" in run


def test_the_actions_lock_lists_both_fix_workflows():
    lock = yaml.safe_load(ACTIONS_LOCK.read_text(encoding="utf-8"))
    assert lock["workflows"][".github/workflows/resync-fix-pushed.yml"] == []
    _, job = _fix_job()
    assert lock["workflows"][".github/workflows/resync-fix-pr.yml"] == [
        _step(job, "Mint the App token")["uses"]]
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
    assert "if" not in _step(job, "Check for the App")


def test_the_fix_routine_leaves_the_pull_request_to_the_workflow():
    guide = (EXPORT_DIR / "FIX-ROUTINE.md").read_text(encoding="utf-8")
    assert "resync-fix-pr.yml" in guide
    assert "Do not open a pull request" in guide


# ── The fire step, run for real against a stub gh ───────────────────────────

HEAD_OLD, HEAD_NEW = "a" * 40, "1" * 40
PR_HEAD = "f" * 40

STUB_GH = """#!/usr/bin/env bash
# Logs every call; answers from files under $STUB. A --jq filter is applied by real jq.
{ printf 'CALL gh token=%s' "${GH_TOKEN:-}"; printf ' [%s]' "$@"; printf '\\n'; } >> "$STUB/log"
jq_expr=""; prev=""
for a in "$@"; do [ "$prev" = --jq ] && jq_expr=$a; prev=$a; done
case "$1 $2" in
  "pr list") src="$STUB/pr-list.json" ;;
  "pr close"|"issue comment") exit 0 ;;
  "api -H") sha=${4##*ref=}; name=${4%%\\?*}; name=${name##*/}
            [ -f "$STUB/head-$sha/$name" ] || { echo '{"message":"SECRET-BODY"}'; exit 1; }
            cat "$STUB/head-$sha/$name"; exit 0 ;;
  "api repos/"*) src="$STUB/comments.json" ;;
  *) echo "unexpected gh call" >&2; exit 9 ;;
esac
jq -r "$jq_expr" "$src"
"""


def _fire_env(tmp_path, *, pull_requests, comments=(), app_token="app-token-value", fetch_ok=True):
    """A sandbox with stubs on PATH; returns (env, cwd, stub dir)."""
    stub = tmp_path / "stub"
    bin_dir = tmp_path / "bin"
    work = tmp_path / "work"
    temp = tmp_path / "runner"
    for d in (stub, bin_dir, work / "export" / "manifests", temp):
        d.mkdir(parents=True, exist_ok=True)
    (bin_dir / "gh").write_text(STUB_GH, encoding="utf-8")
    (bin_dir / "curl").write_text('#!/usr/bin/env bash\necho "curl $*" >> "$STUB/log"\ncat > /dev/null\nprintf 200\n', encoding="utf-8")
    (bin_dir / "date").write_text("#!/usr/bin/env bash\necho 2026-11-25\n", encoding="utf-8")
    for f in bin_dir.iterdir():
        f.chmod(0o755)
    for script in ("resync_stale_fix.py", "resync.py"):
        (work / "export" / script).symlink_to(EXPORT_DIR / script)
    for name, repo, sha in (("one.yml", "src-one", HEAD_NEW), ("two.yml", "src-two", "b" * 40)):
        text = f"repo: {name[:-4]}\nsource: {repo}\nsource_sha: {sha}\n"
        (work / "export" / "manifests" / name).write_text(text, encoding="utf-8")
    (work / "export" / "manifests" / "_common.yml").write_text("protect: []\n", encoding="utf-8")
    (temp / "resync-summary.md").write_text("summary\n", encoding="utf-8")
    (temp / "held-heads.json").write_text(f'{{"src-one": "{HEAD_NEW}"}}', encoding="utf-8")
    (stub / "log").write_text("", encoding="utf-8")
    import json
    (stub / "pr-list.json").write_text(json.dumps(pull_requests), encoding="utf-8")
    (stub / "comments.json").write_text(json.dumps(
        [{"user": {"login": "github-actions[bot]"}, "body": c} for c in comments]), encoding="utf-8")
    if fetch_ok:
        # The PR head's copies: src-one still at the old head, src-two current.
        head = stub / f"head-{PR_HEAD}"
        head.mkdir()
        (head / "one.yml").write_text(f"repo: one\nsource: src-one\nsource_sha: {HEAD_OLD}\n", encoding="utf-8")
        (head / "two.yml").write_text(f"repo: two\nsource: src-two\nsource_sha: {'b' * 40}\n", encoding="utf-8")
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "STUB": str(stub), "RUNNER_TEMP": str(temp),
        "GITHUB_REPOSITORY": "example-owner/kit", "GH_TOKEN": "job-token", "APP_TOKEN": app_token,
        "FIRE_URL": "https://example.com/fire", "FIRE_BEARER": "bearer", "OWNER": "example-owner",
        "ISSUE_NUMBER": "7", "HELD_BACK": "src-one", "RUN_URL": "https://example.com/run/1",
    }
    return env, work, stub


def _fix_pr(number=5, head=PR_HEAD):
    return {"number": number, "headRefName": f"resync-fix/2026-11-2{number}", "headRefOid": head, "isCrossRepository": False}


def _run_fire(env, cwd):
    _, job = _job()
    script = _step(job, "Fire the fix routine")["run"]
    return subprocess.run(["bash", "-c", script], cwd=cwd, env=env, capture_output=True, text=True, timeout=60)


def _log(stub):
    return (stub / "log").read_text(encoding="utf-8")


def _calls(stub, *words):
    """The logged gh calls (a comment spans lines) that start with these words."""
    records = _log(stub).split("CALL ")
    return [r for r in records if r.startswith("gh token=") and r.split(" ", 2)[2].startswith(" ".join(f"[{w}]" for w in words))]


def test_fire_step_closes_a_stale_fix_pull_request_with_the_app_token_then_fires(tmp_path):
    env, cwd, stub = _fire_env(tmp_path, pull_requests=[_fix_pr()])
    done = _run_fire(env, cwd)
    assert done.returncode == 0, done.stderr
    log = _log(stub)
    closes = _calls(stub, "pr", "close")
    assert len(closes) == 1 and closes[0].startswith("gh token=app-token-value [pr] [close] [5]")
    assert "src-one" in closes[0] and "started the fix routine again" in closes[0]
    assert "<sub>🤖 Written by the daily re-sync on behalf of @example-owner</sub>" in closes[0]
    assert log.count("curl ") == 1 and log.index("[pr] [close]") < log.index("curl ")
    marker = _calls(stub, "issue", "comment")
    assert len(marker) == 1 and "<!-- resync-fixer-fired 2026-11-25 -->" in marker[0]
    assert "SECRET-BODY" not in done.stdout + done.stderr


def test_fire_step_with_no_open_fix_pull_request_just_fires(tmp_path):
    env, cwd, stub = _fire_env(tmp_path, pull_requests=[])
    assert _run_fire(env, cwd).returncode == 0
    log = _log(stub)
    assert "[pr] [close]" not in log and log.count("curl ") == 1


def test_fire_step_leaves_a_fresh_fix_pull_request_alone(tmp_path):
    env, cwd, stub = _fire_env(tmp_path, pull_requests=[_fix_pr()])
    (stub / f"head-{PR_HEAD}" / "one.yml").write_text(
        f"repo: one\nsource: src-one\nsource_sha: {HEAD_NEW}\n", encoding="utf-8")
    done = _run_fire(env, cwd)
    assert done.returncode == 0 and "still follows the held sources' heads" in done.stdout
    log = _log(stub)
    assert "[pr] [close]" not in log and "curl " not in log


def test_fire_step_does_nothing_when_todays_marker_is_present_even_with_a_stale_pull_request(tmp_path):
    env, cwd, stub = _fire_env(tmp_path, pull_requests=[_fix_pr()],
                               comments=["Started. <!-- resync-fixer-fired 2026-11-25 -->"])
    done = _run_fire(env, cwd)
    assert done.returncode == 0 and "already started today" in done.stdout
    log = _log(stub)
    assert "[pr] [close]" not in log and "curl " not in log and "[pr] [list]" not in log


def test_fire_step_with_a_stale_pull_request_and_no_app_closes_and_fires_nothing(tmp_path):
    env, cwd, stub = _fire_env(tmp_path, pull_requests=[_fix_pr()], app_token="")
    done = _run_fire(env, cwd)
    assert done.returncode == 0 and "no App to close it" in done.stdout
    log = _log(stub)
    assert "[pr] [close]" not in log and "curl " not in log


def test_fire_step_fails_on_an_unreadable_pull_request_copy_without_printing_a_body(tmp_path):
    env, cwd, stub = _fire_env(tmp_path, pull_requests=[_fix_pr()], fetch_ok=False)
    done = _run_fire(env, cwd)
    assert done.returncode == 1 and "::error::" in done.stdout
    assert "SECRET-BODY" not in done.stdout + done.stderr
    log = _log(stub)
    assert "[pr] [close]" not in log and "curl " not in log
