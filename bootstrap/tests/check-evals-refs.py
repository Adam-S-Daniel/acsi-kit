#!/usr/bin/env python3
"""check-evals-refs.py: no base starter workflow reads skills-evals ungated.

    check-evals-refs.py [<kit root>]

A base-only setup has no skills-evals, so any step of a base starter's
workflow that reads it fails unless EVALS_REPO (a repository variable,
`none` or <owner>/skills-evals) turns it off first (export/DECISIONS.md,
"Base-only track runs green"). This parses every workflow of the five base
starter trees (lib/common.sh's kit_tree of each base repo) with PyYAML and
finds each reference to the eval repository:

  * a `uses:` or `with.repository` / `with.repositories` naming it (a
    checkout of it, a token minted for it, a reusable workflow in it);
  * an `env:` or `with:` value naming <owner>/skills-evals;
  * in a `run:` script, outside shell comment lines, a github.com or
    raw.githubusercontent.com URL, or an API path, of skills-evals or of
    $EVALS_REPO (a clone or a fetch of it). Only this last one looks at text,
    and only for a lexical token: a URL.

Each reference must be gated on EVALS_REPO: its step's or job's `if:` reads
`vars.EVALS_REPO`, or the output of a step or job whose env takes EVALS_REPO
from `vars.EVALS_REPO` (a decision step, run and tested by
check-workflow-gates.py). ALLOW lists the references gated inside their own
script instead, each with why. --self-test runs the scan on a workflow with
an ungated checkout, which must fail. Prints "N assertions passed" and exits
1 on any failure.
"""
import pathlib
import re
import sys
import tempfile

import yaml

KIT = pathlib.Path(__file__).resolve().parent.parent.parent
BASE_TREES = ("agent-guidance", "agent-skills", "agent-skills-private", "repo-settings", "wsl-automation")
FROM_VARS = "${{ vars.EVALS_REPO }}"

# (tree, workflow file, job, step name prefix): references gated inside the
# step's own script, which check-workflow-gates.py runs with EVALS_REPO none,
# unset and set.
ALLOW = {
    # The Loop worker leg exits 0 on EVALS_REPO=none before the pace-hold
    # clone of $EVALS_REPO; the Fleet leg of the same step never clones.
    ("agent-guidance", "fleet-worker-fire.yml", "fire", "Fire the"),
    # Runs on every pull request (it still checks the PR's shape with
    # --no-evidence); with the decision step's on=false it exits before
    # fetching the explorer of $EVALS_REPO.
    ("agent-guidance", "ci.yml", "checks", "Eval-protected sections"),
}

NAME = r"(?:skills-evals|\$\{?EVALS_REPO\}?)"
URL = re.compile(r"(?:github\.com/|githubusercontent\.com/|repos/)(?:[^\s\"'/]+/)?" + NAME + r"(?![\w-])")
LITERAL = re.compile(r"[\w.-]+/skills-evals(?![\w-])")

passed = failed = 0


def check(desc, ok):
    global passed, failed
    if ok:
        passed += 1
    else:
        failed += 1
        print(f"FAIL: {desc}")


def strings(node):
    if isinstance(node, dict):
        for v in node.values():
            yield from strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from strings(v)
    elif node is not None:
        yield str(node)


def references(step):
    """What in this step reads the eval repository, one line per reference."""
    out = []
    uses = str(step.get("uses") or "")
    if LITERAL.search(uses) or "EVALS_REPO" in uses:
        out.append(f"uses {uses}")
    w = step.get("with") or {}
    for key in ("repository", "repositories"):
        if key in w and (LITERAL.search(str(w[key])) or "EVALS_REPO" in str(w[key])):
            out.append(f"with.{key} {w[key]}")
    for key, value in list((step.get("env") or {}).items()) + list(w.items()):
        if key not in ("repository", "repositories") and LITERAL.search(str(value)):
            out.append(f"{key} {value}")
    script = "\n".join(l for l in str(step.get("run") or "").splitlines() if not l.lstrip().startswith("#"))
    out.extend(f"run {m.group(0)}" for m in URL.finditer(script))
    return out


def gate_ids(steps):
    """Ids of the steps whose env takes EVALS_REPO from the variable."""
    return {s["id"] for s in steps if s.get("id") and (s.get("env") or {}).get("EVALS_REPO") == FROM_VARS}


def gated(cond, step_gates, job_gates):
    cond = str(cond or "")
    if "vars.EVALS_REPO" in cond:
        return True
    return any(f"steps.{i}.outputs." in cond for i in step_gates) or \
        any(f"needs.{j}.outputs." in cond for j in job_gates)


def scan(tree_dir, tree):
    """(ungated references, gated count) of one tree's workflows."""
    bad, ok = [], 0
    for wf in sorted((tree_dir / ".github" / "workflows").glob("*.y*ml")):
        doc = yaml.safe_load(wf.read_text(encoding="utf-8")) or {}
        jobs = doc.get("jobs") or {}
        job_gates = {j for j, job in jobs.items() if gate_ids(job.get("steps") or [])}
        for jname, job in jobs.items():
            steps = job.get("steps") or []
            sg = gate_ids(steps)
            job_refs = references(job) if "uses" in job else []
            for r in job_refs:
                if gated(job.get("if"), set(), job_gates):
                    ok += 1
                else:
                    bad.append(f"{tree}/{wf.name} job {jname}: {r}")
            for st in steps:
                refs = references(st)
                if not refs:
                    continue
                name = str(st.get("name") or st.get("uses") or "")
                allowed = any(t == tree and f == wf.name and j == jname and name.startswith(p)
                              for t, f, j, p in ALLOW)
                if allowed or gated(st.get("if"), sg, job_gates) or gated(job.get("if"), set(), job_gates):
                    ok += len(refs)
                else:
                    bad.extend(f"{tree}/{wf.name} job {jname} step {name!r}: {r}" for r in refs)
    return bad, ok


if "--self-test" in sys.argv:
    with tempfile.TemporaryDirectory() as d:
        wf = pathlib.Path(d) / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "x.yml").write_text(
            "on: push\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@v7.0.1\n        with:\n          repository: acme/skills-evals\n"
            "      - run: git clone https://github.com/$EVALS_REPO.git x\n", encoding="utf-8")
        bad, _ = scan(pathlib.Path(d), "self-test")
        check(f"the self-test's two ungated references are found: {bad}", len(bad) == 2)
    sys.exit(1 if failed else 0)

root = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else KIT
total_ok = 0
for tree in BASE_TREES:
    bad, ok = scan(root / "starter" / tree, tree)
    total_ok += ok
    check(f"{tree}: every reference to the eval repository is gated on EVALS_REPO: {bad}", not bad)
for t, f, j, p in ALLOW:
    doc = yaml.safe_load((root / "starter" / t / ".github" / "workflows" / f).read_text(encoding="utf-8"))
    check(f"allowlisted step {t}/{f} {j} {p!r} still exists and still reads EVALS_REPO from the variable",
          any(str(s.get("name", "")).startswith(p) and (s.get("env") or {}).get("EVALS_REPO") == FROM_VARS
              and ("fire" in j or (s.get("env") or {}).get("EVALS_ON") == "${{ steps.evals.outputs.on }}")
              for s in doc["jobs"][j]["steps"]))
check(f"the scan found gated references to check ({total_ok})", total_ok > 0)
print(f"{passed} assertions passed, {failed} failed")
sys.exit(1 if failed else 0)
