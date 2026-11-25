#!/usr/bin/env python3
"""time_zone.py: write the adopter's TIME_ZONE into a staged starter tree.

    time_zone.py <dir> --zone IANA_NAME

The export ships _agent-guidance's scripts/base-md-merge-window.yml with the
neutral zone UTC (export/DECISIONS.md, "The adopter's own time zone"). When the
tree holds that file, this replaces its one `timezone: UTC` line with the
adopter's zone. It fails, changing nothing, when the line is not there exactly
once or the zone is not one python3's tz database loads. A tree without the
file (every other starter) is left alone. Standard library only.
"""
import argparse
import re
import sys
import zoneinfo
from pathlib import Path

WINDOW_REL = Path("scripts") / "base-md-merge-window.yml"
LINE = re.compile(r"^timezone: UTC[ \t]*$", re.MULTILINE)
SHAPE = re.compile(r"^[A-Za-z]+(/[A-Za-z0-9_+-]+)+$|^UTC$")


class ZoneError(Exception):
    pass


def apply_zone(text: str, zone: str) -> str:
    if not SHAPE.fullmatch(zone):
        raise ZoneError(f"TIME_ZONE {zone!r} is not an IANA zone name such as Europe/Berlin")
    try:
        zoneinfo.ZoneInfo(zone)
    except Exception:
        raise ZoneError(f"TIME_ZONE {zone!r} is not a zone this machine's tz database knows") from None
    n = len(LINE.findall(text))
    if n != 1:
        raise ZoneError(f"{WINDOW_REL} has {n} lines reading 'timezone: UTC', not exactly one; "
                        "the starter is not the shape this kit exports")
    return LINE.sub(f"timezone: {zone}", text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tree", type=Path)
    parser.add_argument("--zone", required=True)
    args = parser.parse_args(argv)
    path = args.tree / WINDOW_REL
    if not path.is_file():
        return 0
    try:
        path.write_text(apply_zone(path.read_text(encoding="utf-8"), args.zone), encoding="utf-8")
    except ZoneError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"zone: {WINDOW_REL} is now {args.zone}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
