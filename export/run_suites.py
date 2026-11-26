#!/usr/bin/env python3
"""run_suites.py: run each exported starter tree's own test suite.

Usage: python3 run_suites.py [--kit-name NAME ...] [--keep] [--known-failures FILE]
                            [--owners {invented,one,two}]

For every manifest with a `suite:` block (optionally only the named kit
trees), copies starter/<kit_name>/ to a temporary directory, makes it a git
repository with one commit when `git_init` is set (several suites read their
own history), runs `setup`, then `command`, in a PID namespace so a test that
signals cannot reach a process outside it. Prints one PASS or FAIL line per
tree with the suite's own summary line and exits 1 if any failed. A failing
tree's log is printed in full.

--owners picks the names the copy is given before it runs (owner_forms.py):
`invented` (the default) leaves the tree as exported; `one` runs what
copy-starter.sh runs for a one-account adopter (substitute.py with the second
owner equal to the first, plan_sizing.py, repin.py); `two` does the same for
two accounts whose names sort the other way round, then drops the example
repos' rows as docs/generated-files.md tells an adopter to. The substitution
happens after the copy and before the git commit, so a suite that reads its
own history sees the adopter's tree. A tree that fails to stage fails with
the reason. The PASS or FAIL line names the form when it is not `invented`.

--known-failures FILE names failures that come from the machine running the
suite, not from the export (starter/known-failures.txt): one "<tree> <id>"
per line, where <id> is a pytest summary line without its " - reason"
("FAILED path::test", "SUBFAILED(...) path::test"), a unittest failure
header with its dotted id ("FAIL: module.Class.test", plus " (param=...)"
for a subtest), or a test group the suite's own runner names in "FAILED
GROUPS:" ("group:<name>"). A tree whose command failed passes only when the
failures it names are all listed AND they account for the whole failure:
the pytest summary's failed and error counts, and unittest's "FAILED
(failures=N, errors=M)" totals, equal the ids found, and a failure that
names no id is never excused. A failed group is named "group:<name>" unless
the runner's group table says it "exited N without reporting a failed
assertion" and the output names unittest failures: then its failure is
theirs, and they are the ids to list, so a new test failing in that group
is a new id. Every excused id is printed; a listed id that did not fail is
reported, so the list can be kept short.

A suite whose setup installs Python packages says so with `venv: true`: the
runner then creates a virtual environment under that suite's temporary
directory (`python3 -m venv`), puts it first on the PATH of the suite's setup
and command only, and deletes it with the copy. The trees run at the same
time, so an install into the shared interpreter would uninstall and reinstall
a package another tree's workers are importing (skills-evals' markdown-it-py
pin against agent-skills' and repo-settings': acsi-kit#104). A suite that
installs nothing gets no venv and the plain environment.

The suite's prerequisites (`needs:` in the manifest) are the repo's own;
nothing here installs a system package.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import export  # noqa: E402
import owner_forms  # noqa: E402


def pid_namespace_prefix() -> list:
    """unshare's PID-namespace wrapper, or [] where unshare is unavailable.

    As root the namespace needs no user namespace, and a mapped user
    namespace would break tests that drop privileges with setuid.
    """
    if shutil.which("unshare") is None:
        return []
    base = ["unshare", "--pid", "--fork", "--mount-proc", "--"]
    if os.geteuid() != 0:
        base = ["unshare", "--user", "--map-current-user", "--pid", "--fork", "--mount-proc", "--"]
    probe = subprocess.run(base + ["true"], capture_output=True)
    return base if probe.returncode == 0 else []


# A pytest short-summary line: the outcome (a SUBFAILED one carries its
# subtest's parameters) and the node id, then an optional " - reason".
PYTEST_ID = re.compile(r"^\s*((?:FAILED|ERROR|SUBFAILED\(.*\)) \S+::\S+|(?:FAILED|ERROR) \S+\.py)(?: - .*)?$", re.M)
PYTEST_COUNTS = re.compile(r"^=+ (.*) in [0-9.]+s.*=+$", re.M)
GROUPS = re.compile(r"^\s*FAILED GROUPS: (.+)$", re.M)
# A unittest failure header at the start of a line (a shell runner's own
# "  FAIL: <description>" is indented, so it never matches): the dotted id in
# parentheses, then a subtest's parameters when there are any.
UNITTEST_ID = re.compile(r"^(FAIL|ERROR): \S+ \(([\w.]+)\)( \(.*\))?$", re.M)
UNITTEST_COUNTS = re.compile(r"^FAILED \(([^)]*)\)$", re.M)
# A row of _agent-guidance's run-tests.sh group table, with its note.
GROUP_ROW = re.compile(r"^\s*(\S+)\s+\S+ passed,\s+\S+ failed, exit \S+, \S+s(.*)$", re.M)
EXIT_ONLY = "without reporting a failed assertion"


def _unittest_id(m: re.Match) -> str:
    return f"{m.group(1)}: {m.group(2)}{m.group(3) or ''}"


def failure_ids(out: str) -> tuple[set, str | None]:
    """The failure ids a suite's output names, and a problem when they cannot
    account for the whole failure (None when they do)."""
    pytest_ids = {m.group(1) for m in PYTEST_ID.finditer(out)}
    unittest_hits = [_unittest_id(m) for m in UNITTEST_ID.finditer(out)]
    unittest_ids = set(unittest_hits)
    notes = {m.group(1): m.group(2) for m in GROUP_ROW.finditer(out)}
    group_ids = set()
    for m in GROUPS.finditer(out):
        for g in m.group(1).replace(",", " ").split():
            # The group's only failure is its unittest run's exit: the
            # unittest ids name it, test by test.
            if not (unittest_ids and EXIT_ONLY in notes.get(g, "")):
                group_ids.add(f"group:{g}")
    ids = pytest_ids | unittest_ids | group_ids
    if not ids:
        return ids, "the suite failed without naming a failed test or group"
    counts = PYTEST_COUNTS.findall(out)
    if counts:
        last = counts[-1]
        n = sum(int(x) for x in re.findall(r"(\d+) (?:failed|errors?)\b", last))
        if n != len(pytest_ids):
            return ids, f"pytest reports {n} failed or errored, but {len(pytest_ids)} failure line(s) were found"
    totals = UNITTEST_COUNTS.findall(out)
    if totals or unittest_hits:
        n = sum(int(x) for t in totals for x in re.findall(r"\b(?:failures|errors)=(\d+)", t))
        if n != len(unittest_hits):
            return ids, f"unittest reports {n} failures and errors, but {len(unittest_hits)} failure header(s) were found"
    return ids, None


def load_known(path: Path) -> dict:
    """{tree: {id: line number}} from a known-failures file."""
    known: dict = {}
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            raise SystemExit(f"{path}:{n}: want '<tree> <failure id>'")
        tree, fid = parts
        if fid in known.setdefault(tree, {}):
            raise SystemExit(f"{path}:{n}: {tree} {fid} is listed twice")
        known[tree][fid] = n
    return known


def judge(out: str, known: dict) -> tuple[bool, list]:
    """Whether a failed command's failures are all known; the report lines."""
    ids, problem = failure_ids(out)
    unknown = sorted(ids - set(known))
    lines = [f"known failure (excused): {i}" for i in sorted(ids & set(known))]
    lines += [f"listed as known but did not fail: {i}" for i in sorted(set(known) - ids)]
    lines += [f"NEW FAILURE (not in the known list): {i}" for i in unknown]
    if problem:
        lines.append(f"NOT EXCUSED: {problem}")
    return not unknown and problem is None, lines


def venv_env(env: dict, venv: Path) -> dict:
    """env with the virtual environment at venv active for a child process."""
    out = {k: v for k, v in env.items() if k != "PYTHONHOME"}
    out["VIRTUAL_ENV"] = str(venv)
    out["PATH"] = f"{venv / 'bin'}{os.pathsep}{env.get('PATH', '')}"
    return out


def run_one(kit_name: str, suite: dict, keep: bool, known: dict | None = None,
            owners: str = "invented") -> tuple[bool, str, str, list]:
    src = export.STARTER / kit_name
    tmp = Path(tempfile.mkdtemp(prefix=f"kit-suite-{kit_name}-"))
    work = tmp / kit_name
    log_lines = []
    try:
        shutil.copytree(src, work, symlinks=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "node_modules"))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            owner_forms.stage(work, kit_name, owners)
        except owner_forms.FormError as e:
            return False, f"the {owners} owner form could not be staged: {e}", "", []
        if suite.get("venv"):
            venv = tmp / "venv"
            p = subprocess.run(["python3", "-m", "venv", str(venv)], capture_output=True, text=True, env=env)
            if p.returncode != 0:
                return False, f"venv creation failed: {p.stderr.strip()}", "", []
            env = venv_env(env, venv)
        if suite.get("git_init"):
            for cmd in (["git", "init", "-q", "-b", "main"],
                        ["git", "add", "-A"],
                        ["git", "-c", "user.name=kit", "-c", "user.email=kit@example.com",
                         "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "starter tree"]):
                p = subprocess.run(cmd, cwd=work, capture_output=True, text=True, env=env)
                if p.returncode != 0:
                    return False, f"git setup failed: {p.stderr.strip()}", "", []
        if suite.get("setup"):
            # errexit: a setup is a list of probes and steps, and a failed
            # probe followed by another command (`import ...; if ...; fi`)
            # must stop the setup and name the suite's needs, not leave the
            # suite to fail later with the cause buried in its log.
            p = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", suite["setup"]], cwd=work,
                               capture_output=True, text=True, env=env)
            log_lines.append(p.stdout + p.stderr)
            if p.returncode != 0:
                return False, f"setup exited {p.returncode} (needs: {suite.get('needs', 'see the manifest')})", "".join(log_lines), []
        p = subprocess.run(pid_namespace_prefix() + ["bash", "-c", suite["command"]], cwd=work,
                           capture_output=True, text=True, env=env)
        out = p.stdout + p.stderr
        log_lines.append(out)
        rx = re.compile(suite.get("summary", r"^(Ran \d+ tests.*|OK.*|FAILED.*|\s*Results: .*)$"), re.M)
        summary = "; ".join(m.group(0).strip() for m in rx.finditer(out)) or f"exit {p.returncode}"
        if p.returncode != 0 and known:
            ok, lines = judge(out, known)
            log_lines.append("\n".join(lines) + "\n")
            n = sum(line.startswith("known failure") for line in lines)
            summary += f"; {n} known failure(s) excused" if ok else "; failures not all known"
            return ok, f"{summary} (exit {p.returncode})", "".join(log_lines), lines
        return p.returncode == 0, f"{summary} (exit {p.returncode})", "".join(log_lines), []
    finally:
        if keep:
            print(f"kept {work}", file=sys.stderr)
        else:
            shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--kit-name", nargs="*", help="starter tree names (default: every manifest with a suite)")
    ap.add_argument("--keep", action="store_true", help="keep the temporary copies")
    ap.add_argument("--known-failures", type=Path, help="failures to excuse, by exact id (see the docstring)")
    ap.add_argument("--owners", choices=owner_forms.CHOICES, default="invented",
                    help="the names to give each copy before it runs (default: the export's invented ones)")
    args = ap.parse_args(argv)
    known = load_known(args.known_failures) if args.known_failures else {}
    manifests = export.load_manifests()
    wanted = [m for m in manifests.values() if m.get("suite") and (not args.kit_name or m["kit_name"] in args.kit_name)]
    if args.kit_name:
        missing = set(args.kit_name) - {m["kit_name"] for m in wanted}
        if missing:
            print(f"FAIL: no manifest with a suite for {sorted(missing)}")
            return 1
    failed = 0
    for m in sorted(wanted, key=lambda m: m["kit_name"]):
        ok, summary, log, notes = run_one(m["kit_name"], m["suite"], args.keep, known.get(m["kit_name"]),
                                          args.owners)
        label = m["kit_name"] if args.owners == "invented" else f"{m['kit_name']} ({args.owners})"
        print(f"{'PASS' if ok else 'FAIL'} {label}: {summary}")
        for line in notes:
            print(f"    {line}")
        if not ok:
            failed += 1
            print("\n".join("    " + line for line in log.splitlines()[-200:]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
