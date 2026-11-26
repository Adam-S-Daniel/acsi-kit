"""owner_forms.py: stage a starter tree the way copy-starter.sh does, for run_suites.py.

An adopter's tree has their owner names, not the export's invented ones, and
a one-owner adopter's two owners are one. The kit's CI ran each suite only in
the invented form, so a test that holds for `example-adopter` and
`example-adopter-two` and for nothing else shipped green (DECISIONS,
One-owner fleets). `stage()` gives a copied tree one of three forms:

  invented  the tree as exported (no change);
  one       --owner acme-solo --owner-two ACME-Solo: one account. The case
            difference is deliberate: logins compare case-insensitively, and
            substitute.py's collapse has to see through it;
  two       --owner zeta-user --owner-two Alpha-Org: two accounts whose names
            sort the other way round from the invented ones, and the
            documented "drop the example repos" step done (below).

For `one` and `two` it runs bootstrap/lib/substitute.py, plan_sizing.py
(`--plan pro`), time_zone.py (a zone that is not the export's UTC, ZONES),
the explorer page rebuild for a tree with explorer/display.json (npm ci and
node build.js, then build.js --check, as copy-starter.sh step 2c does: the
pages embed the zone), and repin.py in that order, as copy-starter.sh does;
repin.py is last, because a pin is the digest of a file as the steps before it
left it. Form `two` then
removes the example repos' rows:

  repo-settings   repo-settings/fleet.yml: the `repos:` elements named
                  `<owner>/example-site-*`;
  agent-guidance  repos.yml: the `example-site-*` names of
                  `cron_coverage.fleet` and `skills_bootstrap.repos`.

The rows are found by their node positions in the YAML parser's tree, with
the comment lines directly above each, and the result is checked to load to
exactly the original's data minus those rows. Fewer rows than expected is an
error: a tree that no longer has them needs this table changed.
"""

from __future__ import annotations

import copy
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
BOOTSTRAP_LIB = KIT / "bootstrap" / "lib"

# form -> (owner, owner-two, name, noreply). `invented` is not staged.
FORMS = {
    "one": ("acme-solo", "ACME-Solo", "Acme Solo", "0+acme-solo@users.noreply.github.com"),
    "two": ("zeta-user", "Alpha-Org", "Zeta User", "0+zeta-user@users.noreply.github.com"),
}
CHOICES = ("invented", "one", "two")
# form -> the TIME_ZONE the copy is given: neither is the export's UTC, and one
# is not a whole number of hours from it. Asia/Kolkata is also a name Node's
# Intl renames (to Asia/Calcutta): _agent-guidance's
# scripts/base-md-merge-window.js accepts it since the source's c8cdbd4, which
# the kit's pin includes, so a staged copy proves that fix holds.
ZONES = {"one": "America/Chicago", "two": "Asia/Kolkata"}

EXAMPLE_PREFIX = "example-site-"
# kit tree -> [(file in the tree, key path to the list, rows expected)]
DROPS = {
    "repo-settings": [("repo-settings/fleet.yml", ["repos"], 3)],
    "agent-guidance": [("repos.yml", ["cron_coverage", "fleet"], 3),
                       ("repos.yml", ["skills_bootstrap", "repos"], 3)],
}


class FormError(Exception):
    pass


def _row_name(node) -> str | None:
    """The repo name a list element carries: a scalar's value, or a mapping's
    `name`."""
    import yaml
    if isinstance(node, yaml.ScalarNode):
        return node.value
    if isinstance(node, yaml.MappingNode):
        for k, v in node.value:
            if isinstance(k, yaml.ScalarNode) and k.value == "name" and isinstance(v, yaml.ScalarNode):
                return v.value
    return None


def drop_example_rows(text: str, key_path: list, expected: int) -> str:
    """`text` without the elements of the list at `key_path` whose repo name
    (the part after any `owner/`) starts with `example-site-`, each with the
    comment lines directly above it. Raises FormError unless exactly
    `expected` rows are found and the result loads to the original's data
    minus them."""
    import yaml
    root = yaml.compose(text, Loader=yaml.SafeLoader)
    node = root
    for key in key_path:
        nxt = None
        if isinstance(node, yaml.MappingNode):
            for k, v in node.value:
                if isinstance(k, yaml.ScalarNode) and k.value == key:
                    nxt = v
        if nxt is None:
            raise FormError(f"no `{'.'.join(key_path)}` in the file")
        node = nxt
    if not isinstance(node, yaml.SequenceNode) or node.flow_style:
        raise FormError(f"`{'.'.join(key_path)}` is not a block list")

    lines = text.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))

    def line_of(index):
        # the 0-based line holding character `index`
        lo, hi = 0, len(lines)
        while lo < hi:
            mid = (lo + hi) // 2
            if starts[mid + 1] <= index:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def last_line(item):
        # The line of the item's last leaf: a collection's own end mark sits at
        # the start of whatever follows it.
        leaf = item
        while isinstance(leaf, (yaml.MappingNode, yaml.SequenceNode)) and leaf.value:
            leaf = leaf.value[-1][1] if isinstance(leaf, yaml.MappingNode) else leaf.value[-1]
        return line_of(max(leaf.end_mark.index - 1, 0))

    drop_ranges, gone = [], []
    for n, item in enumerate(node.value):
        name = _row_name(item)
        if name is None or not name.rsplit("/", 1)[-1].startswith(EXAMPLE_PREFIX):
            continue
        first, last = line_of(item.start_mark.index), last_line(item)
        while first > 0 and lines[first - 1].lstrip().startswith("#"):
            first -= 1
        drop_ranges.append((first, last))
        gone.append(n)
    if len(gone) != expected:
        raise FormError(f"expected {expected} `{EXAMPLE_PREFIX}*` row(s) in `{'.'.join(key_path)}`, found {len(gone)}")

    drop = set()
    for first, last in drop_ranges:
        drop.update(range(first, last + 1))
    # A blank line that the cut would leave doubled, or at the end of the file,
    # goes with each run of removed lines.
    runs, run = [], None
    for i in sorted(drop):
        if run and i == run[1] + 1:
            run[1] = i
        else:
            run = [i, i]
            runs.append(run)
    for first, last in runs:
        if last + 1 >= len(lines):
            while first > 0 and not lines[first - 1].strip():
                first -= 1
                drop.add(first)
        elif first > 0 and not lines[first - 1].strip() and not lines[last + 1].strip():
            drop.add(first - 1)
    kept = [ln for i, ln in enumerate(lines) if i not in drop]
    result = "".join(kept)

    want = copy.deepcopy(yaml.safe_load(text))
    target = want
    for key in key_path:
        target = target[key]
    for n in reversed(gone):
        target.pop(n)
    if yaml.safe_load(result) != want:
        raise FormError("the edited YAML does not load to the original's data minus the example rows")
    return result


def drop_example_repos(tree: Path, kit_name: str) -> list:
    """Apply DROPS[kit_name] to the files of the tree at `tree`; the paths
    changed. A tree with no entry is left alone."""
    changed = []
    for rel, key_path, expected in DROPS.get(kit_name, []):
        path = Path(tree) / rel
        if not path.is_file():
            raise FormError(f"{kit_name}: {rel} is not in the tree")
        text = path.read_text(encoding="utf-8")
        path.write_text(drop_example_rows(text, key_path, expected), encoding="utf-8", newline="")
        changed.append(rel)
    return changed


def _run(argv, env=None):
    p = subprocess.run([sys.executable, "-I", *argv], capture_output=True, text=True, env=env)
    if p.returncode != 0:
        raise FormError(f"{Path(argv[0]).name} exited {p.returncode}: {(p.stderr or p.stdout).strip()[-1500:]}")


def rebuild_explorer(tree: Path, env=None) -> None:
    """Rebuild skills-evals' explorer pages from explorer/display.json, as
    copy-starter.sh does after it writes the zone; a tree without it is left alone."""
    explorer = tree / "explorer"
    if not (explorer / "display.json").is_file():
        return
    for argv in (["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund", "--silent"],
                 ["node", "build.js"], ["node", "build.js", "--check"]):
        p = subprocess.run(argv, cwd=explorer, capture_output=True, text=True, env=env)
        if p.returncode != 0:
            raise FormError(f"explorer/: {' '.join(argv)} exited {p.returncode}: {(p.stderr or p.stdout).strip()[-1500:]}")
    shutil.rmtree(explorer / "node_modules", ignore_errors=True)


def stage(tree: Path, kit_name: str, form: str, env=None) -> None:
    """Give the copied tree at `tree` the names and edits of `form`."""
    if form not in CHOICES:
        raise FormError(f"unknown owner form {form!r}; want one of {', '.join(CHOICES)}")
    if form == "invented":
        return
    owner, owner_two, name, noreply = FORMS[form]
    _run([str(BOOTSTRAP_LIB / "substitute.py"), str(tree), "--owner", owner, "--owner-two", owner_two,
          "--name", name, "--noreply", noreply], env)
    _run([str(BOOTSTRAP_LIB / "plan_sizing.py"), str(tree), "--plan", "pro"], env)
    _run([str(BOOTSTRAP_LIB / "time_zone.py"), str(tree), "--zone", ZONES[form]], env)
    rebuild_explorer(tree, env)
    _run([str(BOOTSTRAP_LIB / "repin.py"), str(tree)], env)
    if form == "two":
        drop_example_repos(tree, kit_name)
