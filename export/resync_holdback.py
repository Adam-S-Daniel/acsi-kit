#!/usr/bin/env python3
"""resync_holdback.py: after resync.py moved the pins, hold back any source that breaks the kit.

Usage:
  python3 resync_holdback.py --sources DIR --owner OWNER [--summary FILE]
                             [--tails FILE] [--manifests DIR] [--base-rev REV]

Run it once resync.py has rewritten the manifests. The old pins are the
manifests as committed at --base-rev (default HEAD). Each trial regenerates
starter/ from the manifests as they stand and runs export/tests:

1. every moved source at its new pin; if that passes, nothing is held back;
2. otherwise each moved source alone, the rest at their old pins; a source
   whose trial fails is held back at its old pin;
3. the sources that passed, together; if that still fails, every source is
   held back (an interaction failure) and starter/ goes back to HEAD.

The tree is left in the final state: manifests and starter/ for the pins kept.
A pin is restored by rewriting only the sha text, at the positions
resync.sha_spans reports, so a restored manifest is byte for byte its old self.

Writes, when something is held back: a "Held back" section appended to
--summary (names, pins and compare links, never a log), and the tail of each
failing run to --tails, for a fixer that reads it. That log is deliberately
kept out of the summary, the pull request and the issue: this repository is
public, and a source's output may hold text that must not be copied. When
$GITHUB_OUTPUT is set it gets `held_back=<names>` and `all_held=true|false`.

Exits 0 whenever the run completed, even if every source was held back; 2 on a
bad argument or manifest, 1 on any other internal error.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
MANIFESTS = HERE / "manifests"
TAIL_LINES = 40

_spec = importlib.util.spec_from_file_location("kit_resync", HERE / "resync.py")
resync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(resync)

# Two exports run a source's own Node code (their manifests' regenerate steps),
# and a fetched source has no work tree: the _agent-guidance export runs that
# repo's scripts with NODE_PATH at its node_modules, and the skills-evals
# export builds its explorer pages with esbuild from explorer/node_modules.
# (manifest file, folder in the source checkout, or "" for its root)
NPM_AT_PIN = (("_agent-guidance.yml", ""), ("skills-evals.yml", "explorer"))


class HoldbackError(Exception):
    pass


def tail(text: str, lines: int = TAIL_LINES) -> str:
    return "\n".join(text.splitlines()[-lines:])


# ── The trials ──────────────────────────────────────────────────────────────

class GitRunner:
    """Regenerates starter/ and runs export/tests against the manifests on disk.

    run() returns (passed, tail of the output); reset() puts starter/ back to
    what HEAD has. Every command is an argument array, never a shell string.
    """

    def __init__(self, root: Path, sources: Path, manifests: Path, skip=("agentskills-private",)):
        self.root, self.sources, self.manifests, self.skip = root, sources, manifests, tuple(skip)
        self._installed: dict[tuple[str, str], str] = {}

    def _run(self, args, **kw):
        return subprocess.run(args, cwd=self.root, capture_output=True, text=True, **kw)

    def _git(self, *args):
        return self._run(["git", *args])

    def reset(self) -> None:
        for args in (("reset", "-q", "--", "starter", "export/manifests"),
                     ("checkout", "--", "starter"),
                     ("clean", "-fdq", "--", "starter")):
            done = self._git(*args)
            if done.returncode != 0:
                raise HoldbackError(f"git {args[0]} failed: {done.stderr.strip()}")

    def _npm_at_pin(self, manifest: str, folder: str) -> None:
        text = (self.manifests / manifest).read_text(encoding="utf-8")
        _, source, spans = resync.sha_spans(text, manifest)
        sha = spans[0][2]
        if self._installed.get((source, folder)) == sha:
            return
        checkout = self.sources / source
        pre = f"{folder}/" if folder else ""
        npm_dir = Path(tempfile.mkdtemp(prefix="npm-", dir=os.environ.get("RUNNER_TEMP") or None))
        try:
            for name in ("package.json", "package-lock.json"):
                shown = self._run(["git", "-C", str(checkout), "show", f"{sha}:{pre}{name}"])
                if shown.returncode != 0:
                    raise HoldbackError(shown.stderr)
                (npm_dir / name).write_text(shown.stdout, encoding="utf-8")
            done = self._run(["npm", "ci", "--prefix", str(npm_dir), "--ignore-scripts",
                              "--no-audit", "--no-fund", "--silent"])
            if done.returncode != 0:
                raise HoldbackError(done.stdout + done.stderr)
            target = checkout / folder / "node_modules"
            (checkout / folder).mkdir(parents=True, exist_ok=True)
            shutil.rmtree(target, ignore_errors=True)
            shutil.move(str(npm_dir / "node_modules"), str(target))
        finally:
            shutil.rmtree(npm_dir, ignore_errors=True)
        self._installed[(source, folder)] = sha

    def run(self) -> tuple[bool, str]:
        self.reset()
        try:
            for manifest, folder in NPM_AT_PIN:
                self._npm_at_pin(manifest, folder)
        except HoldbackError as exc:
            return False, tail(f"npm install failed:\n{exc}")
        out = self._run([sys.executable, str(HERE / "export.py"), "--sources", str(self.sources),
                         "--skip", *self.skip])
        if out.returncode != 0:
            return False, tail(out.stdout + out.stderr)
        # Stage new starter files now: export/tests checks every kit file is
        # tracked by git, and a file a source just added is not yet.
        self._git("add", "-A", "--", "export/manifests", "starter")
        out = self._run([sys.executable, "-m", "pytest", "export/tests", "-q", "-p", "no:cacheprovider"])
        return out.returncode == 0, tail(out.stdout + out.stderr)


# ── The hold-back ───────────────────────────────────────────────────────────

@dataclass
class Moved:
    source: str
    old: str      # the source_sha before the re-sync
    new: str      # the head the re-sync moved it to
    names: list = field(default_factory=list)   # manifest files whose pins moved


@dataclass
class Result:
    moved: dict          # source -> Moved
    held: dict           # source -> tail of the failing output
    interaction: bool = False

    @property
    def all_held(self) -> bool:
        return bool(self.moved) and set(self.held) == set(self.moved)


def restore_pins(new_text: str, old_text: str, name: str) -> str:
    """new_text with each pin the re-sync owns put back to old_text's, nothing else touched."""
    _, _, new_spans = resync.sha_spans(new_text, name)
    _, _, old_spans = resync.sha_spans(old_text, name)
    if len(new_spans) != len(old_spans):
        raise HoldbackError(f"{name}: the pins changed shape since HEAD")
    text = new_text
    for (start, end, _), (_, _, old_sha) in sorted(zip(new_spans, old_spans), reverse=True):
        text = text[:start] + old_sha + text[end:]
    return text


def holdback(manifests: Path, old_texts: dict, runner) -> Result:
    """Run the trials; leave the manifests (and, via runner, starter/) in the final state."""
    new_texts = {}
    moved: dict[str, Moved] = {}
    for name in sorted(old_texts):
        new_texts[name] = (manifests / name).read_text(encoding="utf-8")
        if new_texts[name] == old_texts[name]:
            continue
        _, source, new_spans = resync.sha_spans(new_texts[name], name)
        _, _, old_spans = resync.sha_spans(old_texts[name], name)
        m = moved.setdefault(source, Moved(source, old_spans[0][2], new_spans[0][2]))
        m.names.append(name)
    if not moved:
        return Result(moved, {})

    def apply(keep: set) -> None:
        for m in moved.values():
            for name in m.names:
                text = new_texts[name] if m.source in keep else restore_pins(new_texts[name], old_texts[name], name)
                (manifests / name).write_text(text, encoding="utf-8")

    apply(set(moved))
    ok, out = runner.run()
    if ok:
        return Result(moved, {})
    full_tail = out
    held: dict[str, str] = {}
    passing = []
    for source in sorted(moved):
        apply({source})
        ok, out = runner.run()
        if ok:
            passing.append(source)
        else:
            held[source] = out
    if passing and held:
        apply(set(passing))
        ok, out = runner.run()
        if not ok:
            # The sources that failed alone keep their own output; the ones
            # that passed alone get the combination's.
            held = {source: held.get(source, out) for source in moved}
            passing = []
            interaction = True
        else:
            interaction = False
    else:
        # Every source fails alone, or none does and the full set's own
        # failure is an interaction between them.
        interaction = not held
        if interaction:
            held = {source: full_tail for source in moved}
            passing = []
    if not passing:
        apply(set())
        runner.reset()
    return Result(moved, held, interaction)


# ── Reporting ───────────────────────────────────────────────────────────────

def held_markdown(owner: str, result: Result) -> str:
    if not result.held:
        return ""
    lines = ["", "## Held back", ""]
    if result.interaction:
        lines += ["The sources whose new head passed alone still broke the export or its tests "
                  "together, so every moved source stayed at its old pin.", ""]
    else:
        lines += ["These sources stayed at their old pins because their new head broke the export or "
                  "its tests; the others moved.", ""]
    lines += ["| Source | Pinned at | Head it could not take | Compare |", "|---|---|---|---|"]
    for source in sorted(result.held):
        m = result.moved[source]
        url = f"https://github.com/{owner}/{source}/compare/{m.old}...{m.new}"
        lines.append(f"| `{source}` | `{m.old[:12]}` | `{m.new[:12]}` | [compare]({url}) |")
    lines += ["", "The fix routine or a maintainer must follow each held source: change the `edits` entry or "
              "patch in `export/manifests/` that its change broke, record the departure in "
              "`export/DECISIONS.md`, and re-pin it. The daily re-sync tries the head again on every run. "
              "The failing output is not copied here or into the run log (this repository is public): "
              "the fix routine receives it, and a maintainer reproduces it by running the export locally "
              "at the head shown (MAINTAINING.md, Re-pin).", ""]
    return "\n".join(lines)


def tails_text(result: Result) -> str:
    return "".join(f"== {source} ==\n{result.held[source]}\n\n" for source in sorted(result.held))


def write_reports(result: Result, owner: str, summary: Path | None, tails: Path | None, github_output: str | None):
    if result.held:
        if summary:
            with summary.open("a", encoding="utf-8") as fh:
                fh.write(held_markdown(owner, result))
        if tails:
            tails.write_text(tails_text(result), encoding="utf-8")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            fh.write(f"held_back={' '.join(sorted(result.held))}\n")
            fh.write(f"all_held={'true' if result.all_held else 'false'}\n")


def git_old_texts(manifests: Path, rev: str, root: Path) -> dict:
    out = {}
    for path in sorted(manifests.glob("*.yml")):
        if path.name == "_common.yml":
            continue
        shown = subprocess.run(["git", "-C", str(root), "show", f"{rev}:export/manifests/{path.name}"],
                               capture_output=True, text=True)
        if shown.returncode != 0:
            raise HoldbackError(f"{path.name}: not in {rev}")
        out[path.name] = shown.stdout
    return out


def main(argv=None, runner=None, read_old=git_old_texts) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--sources", required=True, type=Path, help="the fetched source checkouts (export.py --sources)")
    ap.add_argument("--owner", required=True, help="the GitHub owner the sources live under (compare links)")
    ap.add_argument("--manifests", type=Path, default=MANIFESTS)
    ap.add_argument("--base-rev", default="HEAD", help="the git revision holding the old pins")
    ap.add_argument("--summary", type=Path, help="append the Held back section to this Markdown file")
    ap.add_argument("--tails", type=Path, help="write the failing output tails here (never into the summary)")
    ap.add_argument("--skip", nargs="*", default=["agentskills-private"])
    args = ap.parse_args(argv)
    if not resync.OWNER.fullmatch(args.owner):
        print(f"resync_holdback.py: not a GitHub owner: {args.owner!r}", file=sys.stderr)
        return 2
    root = HERE.parent
    try:
        old_texts = read_old(args.manifests, args.base_rev, root)
        runner = runner or GitRunner(root, args.sources, args.manifests, args.skip)
        result = holdback(args.manifests, old_texts, runner)
    except resync.ResyncError as exc:
        print(f"resync_holdback.py: {exc}", file=sys.stderr)
        return 2
    except HoldbackError as exc:
        print(f"resync_holdback.py: {exc}", file=sys.stderr)
        return 1
    write_reports(result, args.owner, args.summary, args.tails, os.environ.get("GITHUB_OUTPUT"))
    for source in sorted(result.moved):
        state = "held back" if source in result.held else "moved"
        print(f"{source}: {state}")
    if result.interaction:
        print("interaction failure: every moved source was held back")
    return 0


if __name__ == "__main__":
    sys.exit(main())
