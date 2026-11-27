#!/usr/bin/env python3
"""staged_generated.py <starter tree> --repo-name <name>

Brings two generated values in a staged starter tree in line with the tree
as the steps before it left it (copy-starter.sh runs it after time_zone.py
and before repin.py; export/owner_forms.py does the same for the substituted
forms). A tree that has neither file is left alone.

1. agent-guidance's agents-md/eval-coverage.yml: every row's `bytes` is
   recomputed from its section of the file it names, with the same section
   rule add-content.sh uses (lib/content.py's section_bytes). substitute.py
   gives the starter the adopter's names, which changes a section's length
   whenever a name is longer or shorter than the example's, and that repo's
   CI runs `check-guidance-coverage.js --check-bytes`. A row whose section is
   not in its file is an error.
2. the registry's scripts/skills_waivers.yml: a waiver whose `registry` is
   <name> and whose `path` is not a file of the tree is dropped. The export
   keeps the waivers of the library skills add-content.sh can install; a
   waiver whose skill is not in the copy matches no finding, and the
   registry's conformance census fails on a stale waiver. The file is parsed
   (PyYAML's composer, by node position); only the dropped entries' lines
   change, so the comments stay.

Prints one line per change. Exits 1, changing nothing, on an error.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import content  # noqa: E402  (section_bytes, coverage_with_bytes)

COVERAGE = Path("agents-md") / "eval-coverage.yml"
WAIVERS = Path("scripts") / "skills_waivers.yml"


def coverage(tree: Path) -> tuple[list, list, list]:
    path = tree / COVERAGE
    if not path.is_file():
        return [], [], []
    old = path.read_text(encoding="utf-8")
    new, missing = content.coverage_with_bytes(tree)
    if missing:
        return [], [f"{COVERAGE}: rows with no section in their file: {', '.join(missing)}"], []
    if new == old:
        return [f"unchanged: {COVERAGE}"], [], []
    changed = sum(a != b for a, b in zip(content.lines_of(old), content.lines_of(new)))
    return [f"refreshed: {COVERAGE} ({changed} row(s) of bytes)"], [], [(path, new)]


def _scalar(mapping, key):
    import yaml
    for k, v in mapping.value:
        if isinstance(k, yaml.ScalarNode) and k.value == key:
            return v.value if isinstance(v, yaml.ScalarNode) else None
    return None


def waivers(tree: Path, repo_name: str) -> tuple[list, list, list]:
    path = tree / WAIVERS
    if not path.is_file():
        return [], [], []
    import yaml
    text = path.read_text(encoding="utf-8")
    try:
        root = yaml.compose(text)
    except yaml.YAMLError as e:
        return [], [f"{WAIVERS} is not YAML: {e}"], []
    seq = None
    if isinstance(root, yaml.MappingNode):
        for k, v in root.value:
            if isinstance(k, yaml.ScalarNode) and k.value == "waivers":
                seq = v
    if seq is None or (isinstance(seq, yaml.ScalarNode) and seq.value in ("", "null", "~")):
        return [f"unchanged: {WAIVERS} (no waivers)"], [], []
    if not isinstance(seq, yaml.SequenceNode) or seq.flow_style:
        return [], [f"{WAIVERS}: `waivers` is not a block list"], []
    lines = content.lines_of(text)
    items = seq.value
    drop, out = [], []
    for n, item in enumerate(items):
        if not isinstance(item, yaml.MappingNode):
            return [], [f"{WAIVERS}: waiver {n + 1} is not a mapping"], []
        reg, rel = _scalar(item, "registry"), _scalar(item, "path")
        if reg != repo_name or not rel:
            continue
        try:
            content.safe_rel(rel)
        except content.Refused as e:
            return [], [f"{WAIVERS}: {e}"], []
        if (tree / rel).is_file():
            continue
        # The item's own lines: from its `- ` line through its last value.
        # Its end mark sits where the next token starts (the next item's
        # `- `, or column 0 after a folded scalar), so that line is the next
        # item's unless text before the mark is on it.
        end = item.end_mark.line
        if end < len(lines) and lines[end][:item.end_mark.column].strip():
            end += 1
        # Comments and blank lines after the item belong to what follows.
        while end > item.start_mark.line + 1 and lines[end - 1].strip()[:1] in ("", "#"):
            end -= 1
        drop.append((n, item.start_mark.line, end))
        out.append(f"dropped waiver: {WAIVERS} {rel} (not in this copy)")
    if not drop:
        return [f"unchanged: {WAIVERS}"], [], []
    gone = {n for n, _, _ in drop}
    keep = [ln for i, ln in enumerate(lines) if not any(s <= i < e for _, s, e in drop)]
    if len(gone) == len(items):
        # The list is now empty: write it as [] on the `waivers:` line.
        for i, ln in enumerate(keep):
            if ln.rstrip() == "waivers:":
                keep[i] = "waivers: []\n"
                break
    new = "".join(keep)
    check = yaml.safe_load(new)
    left = [w.get("path") for w in (check or {}).get("waivers") or []]
    want = [_scalar(it, "path") for k, it in enumerate(items) if k not in gone]
    if left != want:
        return [], [f"{WAIVERS}: dropping entries would change the others; left as it is"], []
    return out, [], [(path, new)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("tree", type=Path)
    ap.add_argument("--repo-name", required=True)
    a = ap.parse_args(argv)
    if not a.tree.is_dir():
        print(f"ERROR: {a.tree} is not a directory", file=sys.stderr)
        return 2
    lines, errors, writes = [], [], []
    for result in (coverage(a.tree), waivers(a.tree, a.repo_name)):
        lines += result[0]
        errors += result[1]
        writes += result[2]
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1
    for path, text in writes:
        with open(path, "wb") as f:   # in place: the file keeps its mode
            f.write(text.encode("utf-8"))
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
