#!/usr/bin/env python3
"""fleet_fragment.py: merge repo-settings' fleet.evals.yml into fleet.yml.

    fleet_fragment.py merge <repo-settings clone>
    fleet_fragment.py check <repo-settings clone> <owner>

The repo-settings starter's fleet.yml declares the base repos only; its
repo-settings/fleet.evals.yml holds skills-evals' element (the kit's
export/DECISIONS.md C13). `regenerate.sh evals-fleet` runs `merge` on a
clone and proposes the result; `--check` runs `check` on the default branch.

merge: parses both files with PyYAML and appends each fragment element that
fleet.yml does not already declare (by name) to the end of fleet.yml's
`repos:` list. The element's lines are copied as the fragment has them,
comments included, re-indented to fleet.yml's list indentation. Then it
deletes the fragment. Both files are parsed again before anything is
written: fleet.yml must hold what it held plus exactly the appended
elements, or nothing is written. Idempotent: with no fragment there is
nothing to do; an element fleet.yml already declares is left as it is.

check: exit 0 when fleet.yml declares <owner>/skills-evals exactly once and
no fragment is left; otherwise print `NOT DONE: ...` and exit 1.

Exit 2 on a file that does not parse or has the wrong shape.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

FLEET = "repo-settings/fleet.yml"
FRAGMENT = "repo-settings/fleet.evals.yml"
EVALS_REPO = "skills-evals"


class Refused(Exception):
    pass


def _repos_node(text: str, where: str) -> yaml.SequenceNode:
    try:
        root = yaml.compose(text)
    except yaml.YAMLError as e:
        raise Refused(f"{where} is not valid YAML: {e}") from e
    if not isinstance(root, yaml.MappingNode):
        raise Refused(f"{where}: the top level must be a map")
    seqs = [v for k, v in root.value if isinstance(k, yaml.ScalarNode) and k.value == "repos"]
    if len(seqs) != 1 or not isinstance(seqs[0], yaml.SequenceNode) or seqs[0].flow_style:
        raise Refused(f"{where}: expected one block `repos:` list")
    return seqs[0]


def _last_line(node: yaml.Node) -> int:
    """0-based line of the node's last character (scalars and flow
    collections only: a block collection's end mark is whatever follows)."""
    if isinstance(node, yaml.ScalarNode) or getattr(node, "flow_style", False):
        m = node.end_mark
        return m.line if m.column > 0 else m.line - 1
    children = node.value if isinstance(node, yaml.SequenceNode) else [n for kv in node.value for n in kv]
    return max(_last_line(c) for c in children)


def _name(entry) -> str:
    return str((entry or {}).get("name", "")) if isinstance(entry, dict) else ""


def _load_repos(text: str, where: str) -> list:
    doc = yaml.safe_load(text)
    repos = (doc or {}).get("repos")
    if not isinstance(repos, list):
        raise Refused(f"{where}: `repos:` is not a list")
    return repos


def merged(fleet_text: str, frag_text: str) -> tuple[str, list[str]]:
    """(the new fleet.yml text, the names appended)."""
    fleet_seq = _repos_node(fleet_text, FLEET)
    frag_seq = _repos_node(frag_text, FRAGMENT)
    fleet_repos = _load_repos(fleet_text, FLEET)
    frag_repos = _load_repos(frag_text, FRAGMENT)
    declared = {_name(r).lower() for r in fleet_repos}
    if not fleet_seq.value:
        raise Refused(f"{FLEET}: `repos:` is empty; nothing to append after")
    # fleet.yml's list indentation: the column of its first `- `.
    item_col = fleet_seq.value[0].start_mark.column
    frag_lines = frag_text.splitlines(keepends=True)
    blocks, added, entries = [], [], []
    for node, entry in zip(frag_seq.value, frag_repos):
        name = _name(entry)
        if not name:
            raise Refused(f"{FRAGMENT}: an element has no name")
        if name.lower() in declared:
            continue
        first, last = node.start_mark.line, _last_line(node)
        if frag_lines[first][: node.start_mark.column].strip() != "-":
            raise Refused(f"{FRAGMENT}: {name}'s element does not start its line with `- `")
        shift = item_col - node.start_mark.column
        out = []
        for line in frag_lines[first:last + 1]:
            if not line.strip():
                out.append(line)
            elif shift >= 0:
                out.append(" " * shift + line)
            elif line[: -shift].strip():
                raise Refused(f"{FRAGMENT}: {name}'s element cannot be re-indented to fleet.yml's list")
            else:
                out.append(line[-shift:])
        block = "".join(out)
        blocks.append(block if block.endswith("\n") else block + "\n")
        added.append(name)
        entries.append(entry)
    if not added:
        return fleet_text, []
    lines = fleet_text.splitlines(keepends=True)
    at = _last_line(fleet_seq.value[-1]) + 1
    if at > 0 and not lines[at - 1].endswith("\n"):
        lines[at - 1] += "\n"
    new_text = "".join(lines[:at]) + "".join(blocks) + "".join(lines[at:])
    before, after = yaml.safe_load(fleet_text), yaml.safe_load(new_text)
    if after.get("repos") != fleet_repos + entries:
        raise Refused(f"{FLEET}: the merged list does not parse to the old one plus the fragment's elements")
    if {k: v for k, v in after.items() if k != "repos"} != {k: v for k, v in before.items() if k != "repos"}:
        raise Refused(f"{FLEET}: the merge changed something outside `repos:`")
    return new_text, added


def cmd_merge(clone: Path) -> int:
    fleet, frag = clone / FLEET, clone / FRAGMENT
    if not fleet.is_file():
        raise Refused(f"no {FLEET}: merge the repo-settings starter pull request first")
    if not frag.is_file():
        print(f"{FRAGMENT} is already merged (no such file)")
        return 0
    new_text, added = merged(fleet.read_text(encoding="utf-8"), frag.read_text(encoding="utf-8"))
    if added:
        fleet.write_text(new_text, encoding="utf-8")
    frag.unlink()
    print(f"appended to {FLEET}: {', '.join(added) if added else 'nothing (already declared)'}; removed {FRAGMENT}")
    return 0


def cmd_check(clone: Path, owner: str) -> int:
    fleet, frag = clone / FLEET, clone / FRAGMENT
    if not fleet.is_file():
        raise Refused(f"no {FLEET}: merge the repo-settings starter pull request first")
    want = f"{owner}/{EVALS_REPO}".lower()
    n = sum(_name(r).lower() == want for r in _load_repos(fleet.read_text(encoding="utf-8"), FLEET))
    ok = True
    if n != 1:
        ok = False
        print(f"NOT DONE: {FLEET} declares {owner}/{EVALS_REPO} {n} times (want 1)")
    if frag.is_file():
        ok = False
        print(f"NOT DONE: {FRAGMENT} is still there (merge it into {FLEET})")
    if ok:
        print(f"current: {FLEET} declares {owner}/{EVALS_REPO}, and no fragment is left")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    try:
        if len(argv) == 2 and argv[0] == "merge":
            return cmd_merge(Path(argv[1]))
        if len(argv) == 3 and argv[0] == "check":
            return cmd_check(Path(argv[1]), argv[2])
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    except Refused as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
