#!/usr/bin/env python3
"""time_zone.py: write the adopter's TIME_ZONE into a staged starter tree.

    time_zone.py <dir> --zone IANA_NAME

The export ships two files with the neutral zone UTC: _agent-guidance's
scripts/base-md-merge-window.yml (export/DECISIONS.md, "The adopter's own time
zone") and skills-evals' explorer/display.json (DECISIONS, "Re-pin round 24").
When the tree holds one, this replaces its one `timezone: UTC` line, or its one
`"time_zone": "UTC"` entry, with the adopter's zone. It fails, changing
nothing, when that text is not there exactly once or the zone is not one
python3's tz database loads. A tree with neither file is left alone. The
explorer's pages are built from display.json, so copy-starter.sh rebuilds them
after this changes it. Standard library only.
"""
import argparse
import os
import re
import sys
import zoneinfo
from pathlib import Path

WINDOW_REL = Path("scripts") / "base-md-merge-window.yml"
LINE = re.compile(r"^timezone: UTC[ \t]*$", re.MULTILINE)
DISPLAY_REL = Path("explorer") / "display.json"
DISPLAY_ENTRY = re.compile(r'"time_zone": "UTC"')
# (file, the neutral text, its replacement with the zone)
TARGETS = [
    (WINDOW_REL, LINE, "timezone: {zone}", "lines reading 'timezone: UTC'"),
    (DISPLAY_REL, DISPLAY_ENTRY, '"time_zone": "{zone}"', 'entries reading \'"time_zone": "UTC"\''),
]
SHAPE = re.compile(r"^[A-Za-z]+(/[A-Za-z0-9_+-]+)+$|^UTC$")


class ZoneError(Exception):
    pass


def check_zone(zone: str) -> None:
    if not SHAPE.fullmatch(zone):
        raise ZoneError(f"TIME_ZONE {zone!r} is not an IANA zone name such as Europe/Berlin")
    try:
        zoneinfo.ZoneInfo("UTC")
        nodb = os.environ.get("ACSI_TEST_NO_TZDB") == "1"   # a seam for bootstrap/tests only
    except Exception:
        nodb = True
    if nodb:
        print(f"WARNING: this machine's python3 has no time zone database, so {zone} was checked "
              "for shape only; install one with 'pip install tzdata' for that python3 "
              "(or your OS's tzdata package)", file=sys.stderr)
    else:
        try:
            zoneinfo.ZoneInfo(zone)
        except Exception:
            raise ZoneError(f"TIME_ZONE {zone!r} is not a zone this machine's tz database knows") from None


def apply_zone(text: str, zone: str, rel=WINDOW_REL) -> str:
    check_zone(zone)
    _, pattern, new, what = next(t for t in TARGETS if t[0] == rel)
    n = len(pattern.findall(text))
    if n != 1:
        raise ZoneError(f"{rel} has {n} {what}, not exactly one; "
                        "the starter is not the shape this kit exports")
    return pattern.sub(new.format(zone=zone), text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tree", type=Path)
    parser.add_argument("--zone", required=True)
    args = parser.parse_args(argv)
    found = [rel for rel, *_ in TARGETS if (args.tree / rel).is_file()]
    try:
        new = {rel: apply_zone((args.tree / rel).read_text(encoding="utf-8"), args.zone, rel) for rel in found}
    except ZoneError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    for rel, text in new.items():
        (args.tree / rel).write_text(text, encoding="utf-8")
        print(f"zone: {rel} is now {args.zone}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
