"""DECISIONS X9 for skills-evals: the eval config lists start nearly empty.

`evals/scheduled.yml` schedules fixtures and `evals/non-coverage.yml` records
skip decisions about skills. Each keeps its header comment (the file's
contract) and its one top-level key.

- scheduled.yml keeps the rows of the core items' fixtures, each as the
  source has it (the owner's 2026-10-29 tiers), and unscheduled.yml the rows
  that give a core fixture's reason to be off the schedule. The weekly planner has
  something to run on day one. The optional items' rows went to the library
  (library_fixtures.py); every other row named a fixture the kit does not
  ship and is dropped.
- non-coverage.yml ships `skips: []`: its rows named skills the kit does not
  ship.

Runs on the substituted tree.
"""

from __future__ import annotations

import re
from pathlib import Path

# The core items' fixtures are the ones still in the tree when this runs
# (Content tiers, 2026-10-29): the manifest's excludes dropped the fixtures
# of items the kit does not ship, and library_fixtures.py (which runs first)
# moved the recommended and opinionated items' fixtures and rows out. So a
# row is kept when its fixture folder is in the tree. Re-pin 2026-11-03: the
# source took some core fixtures off the schedule (its evals/unscheduled.yml
# gives each a reason) and scheduled new ones; the rows follow the source.
def _rows(text: str) -> list:
    """(path, block) for each "  - path:" row and the indented lines under it."""
    return [(m.group(1), m.group(0)) for m in re.finditer(r"  - path: (\S+)\n(?:    .*\n)*", text)]


SCHEDULED_NOTE = (
    "#\n"
    "# The kit ships the rows of its core items' fixtures (DECISIONS X9 and\n"
    "# Content tiers); bootstrap/add-content.sh appends an optional item's rows\n"
    "# when you choose it. Add a row when a fixture is ready to run weekly.\n"
)

EMPTY_NOTE = (
    "#\n"
    "# The kit ships this list empty (DECISIONS X9): the rows the source repo\n"
    "# carried named skills an adopter does not have. Add your own.\n"
)


def apply(root: Path, ctx) -> None:
    path = root / "evals/scheduled.yml"
    text = path.read_text(encoding="utf-8")
    head, sep, rows = text.partition("\nfixtures:\n")
    if not sep:
        raise SystemExit("empty_config: evals/scheduled.yml has no top-level `fixtures:` list")
    kept = [b for p, b in _rows(rows) if (root / p / "fixture.yaml").is_file()]
    if not kept:
        raise SystemExit("empty_config: evals/scheduled.yml names none of the core fixtures")
    path.write_text(head + "\n" + SCHEDULED_NOTE + "fixtures:\n" + "".join(kept), encoding="utf-8")

    # evals/unscheduled.yml: the reasons a fixture in the tree is off the
    # schedule; rows for fixtures not in the tree are dropped the same way.
    path = root / "evals/unscheduled.yml"
    text = path.read_text(encoding="utf-8")
    head, sep, rows = text.partition("\nfixtures:\n")
    if not sep:
        raise SystemExit("empty_config: evals/unscheduled.yml has no top-level `fixtures:` list")
    kept = [b for p, b in _rows(rows) if (root / p / "fixture.yaml").is_file()]
    path.write_text(head + ("\nfixtures:\n" + "".join(kept) if kept else "\nfixtures: []\n"), encoding="utf-8")

    # evals/scope-auto.yml: the fixtures the eval scope pass paused, which the
    # source's tests read as scheduled ones; rows for fixtures not in the tree
    # are dropped the same way (re-pin round 5).
    path = root / "evals/scope-auto.yml"
    text = path.read_text(encoding="utf-8")
    head, sep, rows = text.partition("\nrows:\n")
    if not sep:
        raise SystemExit("empty_config: evals/scope-auto.yml has no top-level `rows:` list")
    kept = [b for p, b in _rows(rows) if (root / p / "fixture.yaml").is_file()]
    path.write_text(head + ("\nrows:\n" + "".join(kept) if kept else "\nrows: []\n"), encoding="utf-8")

    path = root / "evals/non-coverage.yml"
    text = path.read_text(encoding="utf-8")
    head, sep, _skips = text.partition("\nskips:\n")
    if not sep:
        raise SystemExit("empty_config: evals/non-coverage.yml has no top-level `skips:` list")
    path.write_text(head + "\n" + EMPTY_NOTE + "skips: []\n", encoding="utf-8")
