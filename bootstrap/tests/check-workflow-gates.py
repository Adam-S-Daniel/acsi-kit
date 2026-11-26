#!/usr/bin/env python3
"""check-workflow-gates.py: the shipped workflows' "turned off" branches work.

A base-only setup has no skills-evals, so _agent-guidance's starter turns
three things off with an explicit `none` (export/DECISIONS.md, "Base-only
track runs green"). This extracts the `run:` script of each step from the
workflow with PyYAML (never a scan of the text) and runs it under bash, with
a fake curl, git, gh and python3 first on PATH and a fake GITHUB_EVENT_PATH.
Nothing touches the network or the clock. Checked:

  fleet-worker-fire.yml, fire step: the Loop worker with EVALS_REPO=none exits
    0 with the skipped notice before any other check (even with no cadence, no
    URL and no bearer) and calls nothing; with EVALS_REPO unset it exits 1
    naming EVALS_REPO and what to set; the Fleet worker ignores it and fires.
  article-watch.yml, watch step: ARTICLE_WATCH_FEED_URL=none exits 0 with a
    notice and calls nothing; unset exits 1 naming it and `none`.
  impact-report.yml, gate step: none writes publish=false and exits 0; unset
    exits 1 naming EVALS_REPO; <owner>/skills-evals writes publish=true; and
    every step after the gate waits on its output.

Each step's env keys are compared with the ones this test supplies, so a new
input fails here rather than running with an unset value. Prints "N
assertions passed" and exits 1 on any failure.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

KIT = Path(__file__).resolve().parent.parent.parent
WF = KIT / "starter" / "agent-guidance" / ".github" / "workflows"
passed = failed = 0


def check(desc, ok):
    global passed, failed
    if ok:
        passed += 1
    else:
        failed += 1
        print(f"FAIL: {desc}")


def load(name, tree="agent-guidance"):
    return yaml.safe_load((KIT / "starter" / tree / ".github" / "workflows" / name).read_text(encoding="utf-8"))


def step_of(doc, job, prefix):
    steps = [s for s in doc["jobs"][job]["steps"] if str(s.get("name", "")).startswith(prefix)]
    assert len(steps) == 1, f"{job}: expected one step named {prefix!r}, found {len(steps)}"
    return steps[0]


def run_step(step, env, event_name="schedule", fakes=("curl", "git", "gh", "python3")):
    """Run the step's script with env; return (rc, stdout, calls made to a fake tool, GITHUB_OUTPUT)."""
    with tempfile.TemporaryDirectory(prefix="gates-") as d:
        d = Path(d)
        log = d / "calls.log"
        for tool in fakes:
            f = d / "bin" / tool
            f.parent.mkdir(exist_ok=True)
            f.write_text(f'#!/usr/bin/env bash\necho "{tool} $*" >> "$CALL_LOG"\ncat >/dev/null || true\n'
                         f'[ "{tool}" = curl ] && printf 200\nexit 0\n', encoding="utf-8")
            f.chmod(0o755)
        event = d / "event.json"
        event.write_text("{}", encoding="utf-8")
        out = d / "github_output"
        out.write_text("", encoding="utf-8")
        run_env = {"PATH": f"{d / 'bin'}{os.pathsep}{os.environ['PATH']}", "CALL_LOG": str(log),
                   "GITHUB_EVENT_NAME": event_name, "GITHUB_EVENT_PATH": str(event),
                   "GITHUB_OUTPUT": str(out), "GITHUB_REPOSITORY": "acme/_agent-guidance", "GITHUB_SHA": "0" * 40,
                   "RUNNER_TEMP": str(d), "HOME": str(d), **env}
        p = subprocess.run(["bash", "-c", step["run"]], env=run_env, capture_output=True, text=True, timeout=60,
                           stdin=subprocess.DEVNULL)
        calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
        return p.returncode, p.stdout + p.stderr, calls, out.read_text(encoding="utf-8")


# ---- fleet-worker-fire.yml
fire_doc = load("fleet-worker-fire.yml")
fire = step_of(fire_doc, "fire", "Fire the")
FIRE_ENV = {"FIRE_URL": "https://api.example.com/fire", "FLEET_BEARER": "fleet-placeholder", "LOOP_BEARER": "loop-placeholder",
            "EVERY_HOURS": "", "WORKER": "fleet", "URL_VAR": "FLEET_WORKER_FIRE_URL", "BEARER_VAR": "FLEET_WORKER_FIRE_BEARER",
            "EVERY_VAR": "FLEET_WORKER_EVERY_HOURS", "EVERY_REQUIRED": "false", "FIRE_TEXT": "test fire", "EVALS_REPO": ""}
check("fire step: env keys are the ones this test supplies", set(fire["env"]) == set(FIRE_ENV))
LOOP = {"WORKER": "loop", "URL_VAR": "LOOP_WORKER_FIRE_URL", "BEARER_VAR": "LOOP_WORKER_FIRE_BEARER",
        "EVERY_VAR": "LOOP_WORKER_EVERY_HOURS", "EVERY_REQUIRED": "true", "EVERY_HOURS": "168"}

NOTICE = "::notice::skipped: EVALS_REPO is none, so there is no eval loop for the Loop worker to serve"
for desc, extra in (("with its usual values", {}),
                    ("with no cadence, no URL and no bearer", {"EVERY_HOURS": "", "FIRE_URL": "", "LOOP_BEARER": ""})):
    rc, out, calls, _ = run_step(fire, {**FIRE_ENV, **LOOP, "EVALS_REPO": "none", **extra})
    check(f"loop worker, EVALS_REPO=none, {desc}: exits 0", rc == 0)
    check(f"loop worker, EVALS_REPO=none, {desc}: prints the skipped notice", NOTICE in out)
    check(f"loop worker, EVALS_REPO=none, {desc}: calls no curl or git", calls == [])
rc, out, calls, _ = run_step(fire, {**FIRE_ENV, **LOOP, "EVALS_REPO": "none"}, event_name="workflow_dispatch")
check("loop worker, EVALS_REPO=none, dispatched: skipped too, nothing called", rc == 0 and NOTICE in out and calls == [])
rc, out, calls, _ = run_step(fire, {**FIRE_ENV, **LOOP, "EVALS_REPO": ""})
check("loop worker, EVALS_REPO unset: exits 1", rc == 1)
check("loop worker, EVALS_REPO unset: names the variable and what to set",
      "variable EVALS_REPO" in out and "none" in out and "<owner>/skills-evals" in out and "create-environments.sh" in out)
check("loop worker, EVALS_REPO unset: calls nothing", calls == [])
rc, out, calls, _ = run_step(fire, {**FIRE_ENV, **LOOP, "EVALS_REPO": "not a repo"})
check("loop worker, EVALS_REPO malformed: exits 1 naming it", rc == 1 and "EVALS_REPO" in out and calls == [])
rc, out, calls, _ = run_step(fire, {**FIRE_ENV, "EVALS_REPO": ""}, event_name="workflow_dispatch")
check("fleet worker, EVALS_REPO unset: still fires", rc == 0 and any(c.startswith("curl ") for c in calls))
rc, out, calls, _ = run_step(fire, {**FIRE_ENV, "EVALS_REPO": "none"}, event_name="workflow_dispatch")
check("fleet worker, EVALS_REPO=none: still fires", rc == 0 and any(c.startswith("curl ") for c in calls) and NOTICE not in out)

# A worker's fire URL of none is "not set up yet" (exit 0, a notice naming the
# step that sets it, nothing called), on its slot or by hand; an empty URL (a
# variable deleted after setup) and a missing bearer keep the real failures.
for role, env, step in (("fleet", FIRE_ENV, 27), ("loop", {**FIRE_ENV, **LOOP, "EVALS_REPO": "acme/skills-evals"}, 41)):
    var = "FLEET_WORKER_FIRE_URL" if role == "fleet" else "LOOP_WORKER_FIRE_URL"
    note = f"::notice::not set up yet: variable {var} is none"
    # (The loop's scheduled case needs a cron line in the event; the starter's
    # own test-fleet-worker-fire.js runs it on one.)
    for ev in (("schedule", "workflow_dispatch") if role == "fleet" else ("workflow_dispatch",)):
        rc, out, calls, _ = run_step(fire, {**env, "FIRE_URL": "none", "FLEET_BEARER": "", "LOOP_BEARER": ""}, event_name=ev)
        check(f"{role} worker, URL none ({ev}): exits 0 with the not-set-up notice naming step {step}",
              rc == 0 and note in out and f"Step {step} of the kit" in out)
        check(f"{role} worker, URL none ({ev}): calls nothing", calls == [])
    rc, out, calls, _ = run_step(fire, {**env, "FIRE_URL": ""}, event_name="workflow_dispatch")
    check(f"{role} worker, URL empty (deleted): still fails naming it", rc == 1 and f"variable {var}" in out and note not in out)
rc, out, calls, _ = run_step(fire, {**FIRE_ENV, "FLEET_BEARER": ""}, event_name="workflow_dispatch")
check("fleet worker, URL set and bearer missing: exits 1 naming the secret",
      rc == 1 and "secret FLEET_WORKER_FIRE_BEARER" in out and calls == [])

# ---- article-watch.yml
aw_doc = load("article-watch.yml")
aw = step_of(aw_doc, "watch", "Fire the routine")
AW_ENV = {"GH_TOKEN": "placeholder", "FEED_URL": "", "FIRE_URL": "https://api.example.com/fire", "FIRE_BEARER": "placeholder"}
check("article watch step: env keys are the ones this test supplies", set(aw["env"]) == set(AW_ENV))
rc, out, calls, _ = run_step(aw, {**AW_ENV, "FEED_URL": "none"})
check("article watch, feed none: exits 0 with the skipped notice", rc == 0 and "::notice::skipped: ARTICLE_WATCH_FEED_URL is none" in out)
check("article watch, feed none: calls nothing", calls == [])
rc, out, calls, _ = run_step(aw, AW_ENV)
check("article watch, feed unset: exits 1 naming it and none",
      rc == 1 and "ARTICLE_WATCH_FEED_URL" in out and "to none to turn the watch off" in out and calls == [])
rc, out, calls, _ = run_step(aw, {**AW_ENV, "FEED_URL": "http://feed.example.com/x"})
check("article watch, a non-https feed: still refused", rc == 1 and "must be an https URL" in out)

# ---- impact-report.yml
ir_doc = load("impact-report.yml")
steps = ir_doc["jobs"]["report"]["steps"]
gate = step_of(ir_doc, "report", "Decide whether")
check("impact report: the gate is the first step", steps[0] is gate or steps[0] == gate)
check("impact report: the gate step is named gate", gate.get("id") == "gate")
check("impact report: every step after the gate waits on its output",
      all(s.get("if") == "steps.gate.outputs.publish == 'true'" for s in steps[1:]))
check("impact report: the publish target is EVALS_REPO", ir_doc["jobs"]["report"]["env"]["PUBLISH_REPO"] == "${{ vars.EVALS_REPO }}")
check("impact report: gate env keys are the ones this test supplies", set(gate["env"]) == {"EVALS_REPO"})
rc, out, calls, gh_out = run_step(gate, {"EVALS_REPO": "none"})
check("impact report, none: exits 0, publish=false, skipped notice",
      rc == 0 and gh_out.strip() == "publish=false" and "::notice::skipped: EVALS_REPO is none" in out)
rc, out, calls, gh_out = run_step(gate, {"EVALS_REPO": ""})
check("impact report, unset: exits 1 naming EVALS_REPO, no output", rc == 1 and "EVALS_REPO" in out and gh_out == "")
rc, out, calls, gh_out = run_step(gate, {"EVALS_REPO": "acme/skills-evals"})
check("impact report, <owner>/skills-evals: publish=true", rc == 0 and gh_out.strip() == "publish=true")
rc, out, calls, gh_out = run_step(gate, {"EVALS_REPO": "acme"})
check("impact report, malformed: exits 1", rc == 1 and gh_out == "")

# ---- the EVALS_REPO decision step two required checks share
EVALS_NOTICE_NONE = "EVALS_REPO is none"


def check_evals_decision(where, step):
    check(f"{where}: decision env keys are EVALS_REPO only", set(step.get("env") or {}) == {"EVALS_REPO"})
    check(f"{where}: EVALS_REPO comes from the repository variable", step["env"]["EVALS_REPO"] == "${{ vars.EVALS_REPO }}")
    rc, out, calls, gh_out = run_step(step, {"EVALS_REPO": "none"}, event_name="pull_request")
    check(f"{where}, none: exits 0, on=false, with a notice", rc == 0 and gh_out.strip() == "on=false" and EVALS_NOTICE_NONE in out)
    rc, out, calls, gh_out = run_step(step, {"EVALS_REPO": ""}, event_name="pull_request")
    check(f"{where}, unset: exits 1 naming EVALS_REPO and what to set",
          rc == 1 and "variable EVALS_REPO" in out and "none" in out and gh_out == "")
    rc, out, calls, gh_out = run_step(step, {"EVALS_REPO": "acme/skills-evals"}, event_name="pull_request")
    check(f"{where}, <owner>/skills-evals: on=true", rc == 0 and gh_out.strip() == "on=true")
    rc, out, calls, gh_out = run_step(step, {"EVALS_REPO": "acme"}, event_name="pull_request")
    check(f"{where}, malformed: exits 1", rc == 1 and gh_out == "")


# _agent-guidance ci.yml, job checks (it feeds the required `test`).
ci_doc = load("ci.yml")
csteps = ci_doc["jobs"]["checks"]["steps"]
dec = step_of(ci_doc, "checks", "Decide whether there is an eval repository")
check_evals_decision("_agent-guidance ci.yml checks", dec)
co = step_of(ci_doc, "checks", "Check out skills-evals")
check("_agent-guidance ci.yml: the skills-evals checkout waits on the decision",
      co.get("if") == "steps.evals.outputs.on == 'true'" and dec.get("id") == "evals")
check("_agent-guidance ci.yml: the checkout reads the repository EVALS_REPO names",
      co["with"]["repository"] == "${{ vars.EVALS_REPO }}")
check("_agent-guidance ci.yml: the decision comes before the checkout", csteps.index(dec) < csteps.index(co))
cov = step_of(ci_doc, "checks", "Section manifest covers")
COV_ENV = {"EVALS_ON": ""}
check("_agent-guidance ci.yml coverage: env keys are the ones this test supplies", set(cov["env"]) == set(COV_ENV))
WITH_NODE = ("curl", "git", "gh", "python3", "node", "jq")
rc, out, calls, _ = run_step(cov, {"EVALS_ON": "false"}, event_name="pull_request", fakes=WITH_NODE)
check("_agent-guidance ci.yml coverage, evals off: runs the check without --skills-evals, with a notice",
      rc == 0 and "::notice::not checked: that each covered row's fixture exists" in out
      and calls == ["node scripts/check-guidance-coverage.js --check-bytes"])
rc, out, calls, _ = run_step(cov, {"EVALS_ON": "true"}, event_name="pull_request", fakes=WITH_NODE)
check("_agent-guidance ci.yml coverage, evals on: checks the fixtures in the checkout",
      rc == 0 and calls == ["node scripts/check-guidance-coverage.js --skills-evals skills-evals --check-bytes"])
ep = step_of(ci_doc, "checks", "Eval-protected sections")
check("_agent-guidance ci.yml eval protection: off means --no-evidence and no explorer fetch",
      "--no-evidence" in ep["run"] and set(ep["env"]) == {"GH_TOKEN", "EVALS_ON", "EVALS_REPO"})
rc, out, calls, _ = run_step(ep, {"GH_TOKEN": "placeholder", "EVALS_ON": "false", "EVALS_REPO": "none"},
                             event_name="pull_request", fakes=WITH_NODE)
check("_agent-guidance ci.yml eval protection, evals off: exits 0 with a notice, runs --no-evidence, fetches nothing",
      rc == 0 and "::notice::not checked: eval protection" in out and not any(c.startswith("curl ") for c in calls)
      and any(c.startswith("node scripts/eval-protected.js ci") and c.endswith("--no-evidence") for c in calls))
rc, out, calls, _ = run_step(ep, {"GH_TOKEN": "placeholder", "EVALS_ON": "true", "EVALS_REPO": "acme/skills-evals"},
                             event_name="pull_request", fakes=WITH_NODE)
check("_agent-guidance ci.yml eval protection, evals on: reads the explorer of the repository EVALS_REPO names",
      rc == 0 and any("raw.githubusercontent.com/acme/skills-evals/persistent/eval-results/explorer/latest.json" in c
                      for c in calls if c.startswith("curl ")))

# acsi-agentskills ci.yml, job pytest (it feeds merge-gate).
as_doc = load("ci.yml", "agent-skills")
asteps = as_doc["jobs"]["pytest"]["steps"]
adec = step_of(as_doc, "pytest", "Decide whether there is an eval repository")
check_evals_decision("acsi-agentskills ci.yml pytest", adec)
for prefix in ("Check out the eval-protection gate", "Eval-protected skills"):
    st = step_of(as_doc, "pytest", prefix)
    check(f"acsi-agentskills ci.yml: {prefix!r} waits on the decision",
          st.get("if") == "github.event_name == 'pull_request' && steps.evals.outputs.on == 'true'"
          and asteps.index(adec) < asteps.index(st))

# The scheduled-run-health callers: no schedule while the reusable sits at
# the forty-zero placeholder (regenerate.sh run-health-sha adds both).
for tree in ("agent-skills", "repo-settings", "wsl-automation"):
    doc = load("scheduled-run-health.yml", tree)
    on = doc.get("on", doc.get(True))
    uses = doc["jobs"]["audit"]["uses"]
    check(f"{tree} scheduled-run-health.yml: no schedule while it calls the placeholder sha",
          not ("@" + "0" * 40 in uses and "schedule" in on))

# repo-settings.yml's plan job before the settings-read App exists.
rs_doc = load("repo-settings.yml", "repo-settings")
plan = rs_doc["jobs"]["plan"]["steps"]
ra = step_of(rs_doc, "plan", "Is the read App set up yet")
check("repo-settings plan: the read App check comes before every mint", all(
    plan.index(ra) < plan.index(s) for s in plan if "create-github-app-token" in str(s.get("uses", ""))))
for s in plan:
    if "create-github-app-token" in str(s.get("uses", "")) or str(s.get("id", "")).startswith("plan_") \
            or s.get("id") == "coverage" or "gh issue" in str(s.get("run", "")):
        check(f"repo-settings plan: {s.get('name')!r} waits on the read App check",
              s.get("if") == "steps.read_app.outputs.ready == 'true'")
check("repo-settings plan: read App check env is the client id variable",
      ra.get("env") == {"READ_APP_CLIENT_ID": "${{ vars.REPO_SETTINGS_READ_APP_CLIENT_ID }}"})
rc, out, calls, gh_out = run_step(ra, {"READ_APP_CLIENT_ID": ""})
check("repo-settings plan, read App unset on schedule: exits 0, ready=false, a not-set-up notice naming the variable",
      rc == 0 and gh_out.strip() == "ready=false" and "REPO_SETTINGS_READ_APP_CLIENT_ID" in out and "not set up yet" in out)
for ev in ("push", "workflow_dispatch"):
    rc, out, calls, gh_out = run_step(ra, {"READ_APP_CLIENT_ID": ""}, event_name=ev)
    check(f"repo-settings plan, read App unset on {ev}: ready=true, so the mint fails as in the source",
          rc == 0 and gh_out.strip() == "ready=true" and "not set up yet" not in out)
rc, out, calls, gh_out = run_step(ra, {"READ_APP_CLIENT_ID": "Iv1.placeholder"})
check("repo-settings plan, read App set: ready=true", rc == 0 and gh_out.strip() == "ready=true")

# drift-report.yml and dependabot-config-health.yml name a missing App
# installation (step 7 may be the adopter's answer) and how to undo the mark.
for wf, job, level in (("drift-report.yml", "report", "::warning::"), ("dependabot-config-health.yml", "sweep", "::error::")):
    st = step_of(load(wf), job, "Name a missing App installation")
    base_env = {"GH_TOKEN_EXAMPLE_ADOPTER": "", "GH_TOKEN_EXAMPLE_ADOPTER_TWO": "", "SYNC_OWNERS": "example-adopter"}
    check(f"{wf}: the installation step's env keys are the ones this test supplies", set(st["env"]) == set(base_env))
    rc, out, calls, _ = run_step(st, base_env)
    check(f"{wf}: a missing token names the App, the settings page and status.sh --unmark 7",
          rc == 0 and level + "No installation token for example-adopter" in out
          and "https://github.com/settings/installations" in out and "status.sh --unmark 7" in out and calls == [])
    rc, out, calls, _ = run_step(st, {**base_env, "GH_TOKEN_EXAMPLE_ADOPTER": "token-canary"})
    check(f"{wf}: with a token it says nothing and never prints it", rc == 0 and out.strip() == "")

print(f"{passed} assertions passed, {failed} failed")
sys.exit(1 if failed else 0)
