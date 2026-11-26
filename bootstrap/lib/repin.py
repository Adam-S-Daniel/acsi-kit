#!/usr/bin/env python3
"""repin.py <starter tree>

Recomputes the sha256 pins inside a staged starter tree that name another
file of the same tree, after lib/substitute.py changed that file's bytes
(copy-starter.sh runs it right after plan_sizing.py; export/run_suites.py runs
it for the substituted forms). The export wrote each pin as the digest of the
file as exported, and the tree's own tests recompute it from the bytes the
adopter's names produced.

PINS is the table. Each row names a file that holds one pin line, the line's
shape, and the file whose digest it holds:

  agent-skills        scripts/cloud-env-setup.sh `fleet_pin_sha256=<digest>`
                      <- plugins/acsi-anything-anywhere/hooks/fleet-guidance/fleet-memory.sh
  agent-guidance      docs/codex-cloud.md `fleet_pin_sha256=<digest>`
                      <- .claude/hooks/fleet-memory.sh

Only the digest is replaced. The `fleet_pin_commit=` beside it names a commit
of the owner's repository, which this does not know, and stays as exported.

A tree that has none of the pin files is left alone (every other starter).
A tree that has a pin file must also have the file it digests and exactly one
pin line of the right shape in it, or this exits 1 and changes nothing: a
table row that no longer matches the tree is an error, not a skip. Prints one
line per pin. Standard library only.
"""
import hashlib
import re
import sys
from pathlib import Path

# (pin file, regex whose one group is the 64-hex digest, file the digest is of)
PINS = (
    ("scripts/cloud-env-setup.sh",
     r"(?m)^fleet_pin_sha256=([0-9a-f]{64})$",
     "plugins/acsi-anything-anywhere/hooks/fleet-guidance/fleet-memory.sh"),
    ("docs/codex-cloud.md",
     r"(?m)^fleet_pin_sha256=([0-9a-f]{64})$",
     ".claude/hooks/fleet-memory.sh"),
)


def repin(root):
    """Rewrite each pin in `root`; returns (lines to print, errors). Writes
    nothing when there is an error."""
    root = Path(root)
    lines, errors, writes = [], [], []
    for pin_file, pattern, target in PINS:
        pin_path = root / pin_file
        if not pin_path.is_file():
            continue
        target_path = root / target
        if not target_path.is_file():
            errors.append(f"{pin_file} pins {target}, which is not in the tree")
            continue
        text = pin_path.read_bytes().decode("utf-8")
        found = list(re.finditer(pattern, text))
        if len(found) != 1:
            errors.append(f"{pin_file} has {len(found)} pin line(s) of the shape {pattern!r}, want exactly 1")
            continue
        want = hashlib.sha256(target_path.read_bytes()).hexdigest()
        old = found[0].group(1)
        if old == want:
            lines.append(f"unchanged: {pin_file} ({want[:12]})")
            continue
        start, end = found[0].span(1)
        writes.append((pin_path, text[:start] + want + text[end:]))
        lines.append(f"repinned: {pin_file} {old[:12]} -> {want[:12]} ({target})")
    return lines, errors, writes


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0].startswith("-"):
        print(__doc__.split("\n\n")[0], file=sys.stderr)
        return 2
    if not Path(argv[0]).is_dir():
        print(f"ERROR: {argv[0]} is not a directory", file=sys.stderr)
        return 2
    lines, errors, writes = repin(argv[0])
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
